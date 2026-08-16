from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_robustness import matched_with_coverage
from packages.gexy.tradeflow_window_regime import assign_session_window


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
MIN_VOLUME_COVERAGE = 0.90
TARGET = "forward_return_15m_bps"
HEDGE_SIGNAL = "hedge_delta_units"
EARLY_START = "09:31"
EARLY_END = "09:40"
LOCAL_TZ = "America/New_York"

FROZEN_DEVELOPMENT_DATES = (
    "2026-08-13",
    "2026-08-12",
    "2026-08-11",
    "2026-08-10",
    "2026-08-07",
    "2026-08-06",
    "2026-08-05",
    "2026-08-04",
    "2026-08-03",
    "2026-07-31",
    "2026-07-30",
    "2026-07-29",
    "2026-07-28",
    "2026-07-27",
    "2026-07-24",
    "2026-07-23",
    "2026-07-22",
)

RESERVED_HOLDOUT_DATES = (
    "2026-07-21",
    "2026-07-20",
    "2026-07-17",
)

DESCRIPTORS = (
    "early_forward_return_bps",
    "early_hedge_delta_imbalance",
    "early_raw_contract_imbalance",
    "early_hedge_gex_imbalance",
    "early_classified_contract_volume",
    "early_gross_abs_delta_notional",
)


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def _spearman(x: pd.Series, y: pd.Series) -> float:
    frame = pd.DataFrame(
        {
            "x": pd.to_numeric(x, errors="coerce"),
            "y": pd.to_numeric(y, errors="coerce"),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return float("nan")
    return float(
        frame["x"].rank(method="average").corr(
            frame["y"].rank(method="average"), method="pearson"
        )
    )


def _safe_sum(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns:
        raise ValueError(f"early state frame missing required column: {column}")
    values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    if values.notna().sum() == 0:
        return float("nan")
    return float(values.sum(skipna=True))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def _opening_sample(raw: pd.DataFrame, hedge: pd.DataFrame) -> pd.DataFrame:
    sample = matched_with_coverage(raw, hedge, min_volume_coverage=MIN_VOLUME_COVERAGE)
    sample = assign_session_window(sample)
    sample = sample.loc[sample["session_window"] == "opening"].copy()
    return sample.reset_index(drop=True)


def _endpoint_b(sample: pd.DataFrame) -> tuple[int, float]:
    required = [HEDGE_SIGNAL, TARGET]
    missing = [column for column in required if column not in sample.columns]
    if missing:
        raise ValueError("opening sample missing endpoint columns: " + ", ".join(missing))
    complete = sample[required].apply(pd.to_numeric, errors="coerce")
    complete = complete.replace([np.inf, -np.inf], np.nan).dropna()
    if len(complete) < 3:
        raise ValueError("fewer than 3 complete opening endpoint observations")
    return int(len(complete)), _spearman(complete[HEDGE_SIGNAL], complete[TARGET])


def _early_sample(sample: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in sample.columns:
        raise ValueError("opening sample missing timestamp")
    frame = sample.copy()
    timestamp = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.loc[timestamp.notna()].copy()
    local = timestamp.loc[timestamp.notna()].dt.tz_convert(LOCAL_TZ)
    minutes = local.dt.strftime("%H:%M")
    frame = frame.loc[(minutes >= EARLY_START) & (minutes <= EARLY_END)].copy()
    return frame.sort_values("timestamp").reset_index(drop=True)


def _day_descriptors(sample: pd.DataFrame) -> dict[str, float | int]:
    early = _early_sample(sample)
    if early.empty:
        raise ValueError("no causal early-opening rows between 09:31 and 09:40")

    forward = pd.to_numeric(early.get("forward"), errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    if len(forward) >= 2 and float(forward.iloc[0]) != 0:
        early_forward_return_bps = float(
            (float(forward.iloc[-1]) / float(forward.iloc[0]) - 1.0) * 10000.0
        )
    else:
        early_forward_return_bps = float("nan")

    hedge_delta_notional = _safe_sum(early, "hedge_delta_notional")
    gross_delta_notional = _safe_sum(early, "hedge_gross_abs_delta_notional")
    net_signed_contracts = _safe_sum(early, "flow_net_signed_contracts")
    classified_contract_volume = _safe_sum(early, "flow_classified_contract_volume")
    hedge_gex = _safe_sum(early, "hedge_gex_notional_per_1pct")
    gross_gex = _safe_sum(early, "hedge_gross_abs_gex_notional_per_1pct")

    return {
        "early_rows": int(len(early)),
        "early_forward_return_bps": early_forward_return_bps,
        "early_hedge_delta_imbalance": _safe_ratio(
            hedge_delta_notional, gross_delta_notional
        ),
        "early_raw_contract_imbalance": _safe_ratio(
            net_signed_contracts, classified_contract_volume
        ),
        "early_hedge_gex_imbalance": _safe_ratio(hedge_gex, gross_gex),
        "early_classified_contract_volume": classified_contract_volume,
        "early_gross_abs_delta_notional": gross_delta_notional,
    }


def _screen_descriptor(day_table: pd.DataFrame, descriptor: str) -> dict[str, object]:
    pair = day_table[[descriptor, "endpoint_b_ordinary_spearman"]].copy()
    pair[descriptor] = pd.to_numeric(pair[descriptor], errors="coerce")
    pair["endpoint_b_ordinary_spearman"] = pd.to_numeric(
        pair["endpoint_b_ordinary_spearman"], errors="coerce"
    )
    pair = pair.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)

    full = _spearman(pair[descriptor], pair["endpoint_b_ordinary_spearman"])
    loo: list[float] = []
    for index in range(len(pair)):
        subset = pair.drop(index=index).reset_index(drop=True)
        value = _spearman(subset[descriptor], subset["endpoint_b_ordinary_spearman"])
        if np.isfinite(value):
            loo.append(float(value))

    array = np.asarray(loo, dtype=float)
    full_sign = int(np.sign(full)) if np.isfinite(full) else 0
    if len(array):
        loo_signs = np.sign(array).astype(int)
        sign_consistent = int(np.sum(loo_signs == full_sign)) if full_sign != 0 else 0
        opposite = bool(np.any((loo_signs != 0) & (loo_signs == -full_sign))) if full_sign else False
        loo_median = float(np.median(array))
        loo_min = float(np.min(array))
        loo_max = float(np.max(array))
    else:
        sign_consistent = 0
        opposite = False
        loo_median = loo_min = loo_max = float("nan")

    loo_count = int(len(array))
    sign_consistency_pct = (
        float(sign_consistent / loo_count) if loo_count else float("nan")
    )
    eligible = bool(
        len(pair) >= 15
        and np.isfinite(full)
        and abs(full) >= 0.35
        and np.isfinite(sign_consistency_pct)
        and sign_consistency_pct >= 0.80
        and not (loo_count >= 16 and opposite)
    )

    return {
        "descriptor": descriptor,
        "finite_day_pairs": int(len(pair)),
        "spearman_vs_endpoint_b": float(full),
        "abs_spearman": abs(float(full)) if np.isfinite(full) else float("nan"),
        "loo_count": loo_count,
        "loo_sign_consistent_count": sign_consistent,
        "loo_sign_consistency_pct": sign_consistency_pct,
        "loo_median": loo_median,
        "loo_min": loo_min,
        "loo_max": loo_max,
        "loo_any_opposite_sign": opposite,
        "eligible": eligible,
    }


def _select_candidate(summary: pd.DataFrame) -> str | None:
    eligible = summary.loc[summary["eligible"].astype(bool)].copy()
    if eligible.empty:
        return None
    eligible["abs_spearman"] = pd.to_numeric(eligible["abs_spearman"], errors="coerce")
    eligible = eligible.sort_values(
        ["abs_spearman", "descriptor"], ascending=[False, True]
    )
    return str(eligible.iloc[0]["descriptor"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen GEXY development-only early-opening session-state screen. "
            "Uses exactly 17 already-seen dates, a 09:40 causal cutoff, six frozen descriptors, "
            "the continuous ordinary 15m Endpoint-B Spearman target, and no market-data request. "
            "At most one descriptor may be selected; reserved holdout dates are not read."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing existing local raw-flow and hedge-flow feature CSVs",
    )
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    missing: list[str] = []
    for day in FROZEN_DEVELOPMENT_DATES:
        raw_path = _raw_path(args.data_dir, day)
        hedge_path = _hedge_path(args.data_dir, day)
        if not raw_path.exists():
            missing.append(str(raw_path))
        if not hedge_path.exists():
            missing.append(str(hedge_path))
    if missing:
        raise SystemExit(
            "SESSION-STATE DEVELOPMENT ABORTED: missing frozen local inputs: "
            + ", ".join(missing)
        )

    for day in FROZEN_DEVELOPMENT_DATES:
        raw = pd.read_csv(_raw_path(args.data_dir, day))
        hedge = pd.read_csv(_hedge_path(args.data_dir, day))
        sample = _opening_sample(raw, hedge)
        observations, endpoint_b = _endpoint_b(sample)
        descriptors = _day_descriptors(sample)
        rows.append(
            {
                "trading_day": day,
                "endpoint_observations": observations,
                "endpoint_b_ordinary_spearman": endpoint_b,
                **descriptors,
            }
        )

    day_table = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [_screen_descriptor(day_table, descriptor) for descriptor in DESCRIPTORS]
    )
    selected = _select_candidate(summary)

    args.data_dir.mkdir(parents=True, exist_ok=True)
    day_output = args.data_dir / "gexy_spxw_session_state_development_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_session_state_development_screen.csv"
    day_table.to_csv(day_output, index=False)
    summary.to_csv(summary_output, index=False)

    print("GEXY SESSION-STATE DEVELOPMENT SCREEN — FROZEN DEVELOPMENT-ONLY")
    print(f"DEVELOPMENT DATES: {','.join(FROZEN_DEVELOPMENT_DATES)}")
    print(f"RESERVED UNTOUCHED HOLDOUT: {','.join(RESERVED_HOLDOUT_DATES)}")
    print("OPENING ENDPOINT: ordinary hedge_delta_units vs forward_return_15m_bps Spearman")
    print("MIN CLASSIFIED-VOLUME GREEK COVERAGE: 90%")
    print("EARLY STATE CUTOFF: 09:40 America/New_York; M+1 completed flow through 09:39 only")
    print("CANDIDATES: exactly six frozen univariate descriptors; no combinations")
    print("STATUS: development-only on already-seen dates; not out-of-sample validation")

    display_day = [
        "trading_day",
        "endpoint_observations",
        "endpoint_b_ordinary_spearman",
        "early_rows",
        *DESCRIPTORS,
    ]
    print("\nDEVELOPMENT DAY TABLE")
    print(day_table[display_day].to_string(index=False))

    print("\nFROZEN UNIVARIATE SCREEN")
    print(summary.to_string(index=False))

    if selected is None:
        print("\nSELECTED CANDIDATE: NONE")
        print("HOLDOUT ACTION: do not purchase or evaluate the reserved holdout block under this protocol.")
    else:
        selected_row = summary.loc[summary["descriptor"] == selected].iloc[0]
        sign_text = "positive" if float(selected_row["spearman_vs_endpoint_b"]) > 0 else "negative"
        print(f"\nSELECTED CANDIDATE: {selected}")
        print(f"FROZEN EXPECTED MONOTONIC SIGN FOR FUTURE HOLDOUT: {sign_text}")
        print("HOLDOUT ACTION: freeze a separate acquisition/validation protocol before any reserved-date purchase.")

    print(f"\nBY-DAY CSV: {day_output}")
    print(f"SCREEN CSV: {summary_output}")
    print("NO PAID DATA REQUESTS: this screen reads only existing local feature CSVs.")
    print("NO HOLDOUT INSPECTION: reserved 2026-07-21, 2026-07-20, and 2026-07-17 are not read.")
    print("INTERPRETATION LIMIT: development correlations do not establish causality, regime mechanism, or production edge.")


if __name__ == "__main__":
    main()
