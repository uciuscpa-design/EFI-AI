from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_batch4_heterogeneity import (
    HEDGE,
    MOMENTUM,
    RAW,
    TARGET,
    _spearman,
    frozen_opening_sample,
)
from packages.gexy.tradeflow_hedge_incremental import partial_spearman
from packages.gexy.tradeflow_window_regime import assign_session_window


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
HOLDOUT_DATES = ("2026-07-21", "2026-07-20", "2026-07-17")
CHRONOLOGICAL_HOLDOUT_DATES = ("2026-07-17", "2026-07-20", "2026-07-21")
SEEN_DATES = (
    "2026-07-22",
    "2026-07-23",
    "2026-07-24",
    "2026-07-27",
    "2026-07-28",
    "2026-07-29",
    "2026-07-30",
    "2026-07-31",
    "2026-08-03",
    "2026-08-04",
    "2026-08-05",
    "2026-08-06",
    "2026-08-07",
    "2026-08-10",
    "2026-08-11",
    "2026-08-12",
    "2026-08-13",
)
MIN_VOLUME_COVERAGE = 0.90
FROZEN_HORIZON_MINUTES = 15
AUGUST_REFERENCE_MEDIAN = -0.209360
ROLLING_WINDOW = 5
EXPECTED_OPENING_ROWS = 30
EXPECTED_ELIGIBLE_ROWS = 29
EXPECTED_EXCLUDED_FLOW_MINUTE_UTC = "13:30:00"


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def _seen_chronology_path(data_dir: Path) -> Path:
    return data_dir / "gexy_spxw_chronological_drift_by_day.csv"


def _truthy(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _ordinary_loo_values(sample: pd.DataFrame) -> np.ndarray:
    values: list[float] = []
    for index in range(len(sample)):
        subset = sample.drop(index=index).reset_index(drop=True)
        value = _spearman(subset[HEDGE], subset[TARGET])
        if np.isfinite(value):
            values.append(float(value))
    return np.asarray(values, dtype=float)


def _classify(full_value: float, loo: np.ndarray) -> tuple[str, int, float]:
    if not np.isfinite(full_value) or full_value == 0 or len(loo) == 0:
        return "sign_fragile", 0, float("nan")
    sign = int(np.sign(full_value))
    loo_signs = np.sign(loo).astype(int)
    same_count = int(np.sum(loo_signs == sign))
    same_pct = float(same_count / len(loo))
    strict = bool(np.all(loo_signs == sign))
    if strict and sign > 0:
        return "strict_sign_stable_positive", same_count, same_pct
    if strict and sign < 0:
        return "strict_sign_stable_negative", same_count, same_pct
    return "sign_fragile", same_count, same_pct


def _safe_holdout_preflight(data_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for day in HOLDOUT_DATES:
        raw_path = _raw_path(data_dir, day)
        hedge_path = _hedge_path(data_dir, day)
        if not raw_path.exists():
            raise ValueError(f"missing raw causal trade-flow feature CSV: {raw_path}")
        if not hedge_path.exists():
            raise ValueError(f"missing hedge-flow feature CSV: {hedge_path}")

        raw_headers = set(pd.read_csv(raw_path, nrows=0).columns)
        hedge_headers = set(pd.read_csv(hedge_path, nrows=0).columns)
        raw_required = {"timestamp", "flow_minute", RAW, MOMENTUM, TARGET}
        hedge_required = {
            "timestamp",
            "flow_minute",
            HEDGE,
            TARGET,
            "replay_match",
            "hedge_greek_solved_contract_volume_pct",
        }
        missing_raw = sorted(raw_required.difference(raw_headers))
        missing_hedge = sorted(hedge_required.difference(hedge_headers))
        if missing_raw:
            raise ValueError(f"{day}: raw feature CSV missing columns: {', '.join(missing_raw)}")
        if missing_hedge:
            raise ValueError(f"{day}: hedge feature CSV missing columns: {', '.join(missing_hedge)}")

        # Holdout-safe read: do not read any forward-return label values.
        safe = pd.read_csv(
            hedge_path,
            usecols=[
                "flow_minute",
                "timestamp",
                "replay_match",
                "hedge_greek_solved_contract_volume_pct",
            ],
        )
        safe = assign_session_window(safe)
        safe = safe.loc[safe["session_window"] == "opening"].copy()
        replay = _truthy(safe["replay_match"])
        coverage = pd.to_numeric(
            safe["hedge_greek_solved_contract_volume_pct"], errors="coerce"
        )
        eligible = replay & (coverage >= MIN_VOLUME_COVERAGE)
        excluded = safe.loc[replay & (coverage < MIN_VOLUME_COVERAGE)].copy()

        if len(safe) != EXPECTED_OPENING_ROWS:
            raise ValueError(
                f"{day}: expected {EXPECTED_OPENING_ROWS} opening rows from frozen preparation; found {len(safe)}"
            )
        if int(replay.sum()) != EXPECTED_OPENING_ROWS:
            raise ValueError(
                f"{day}: expected {EXPECTED_OPENING_ROWS}/{EXPECTED_OPENING_ROWS} replay matches; found {int(replay.sum())}/{len(safe)}"
            )
        if int(eligible.sum()) != EXPECTED_ELIGIBLE_ROWS:
            raise ValueError(
                f"{day}: expected {EXPECTED_ELIGIBLE_ROWS} rows at >=90% Greek-volume coverage; found {int(eligible.sum())}"
            )
        if len(excluded) != 1:
            raise ValueError(f"{day}: expected exactly one below-90% opening row; found {len(excluded)}")

        excluded_flow = pd.to_datetime(excluded.iloc[0]["flow_minute"], utc=True, errors="coerce")
        excluded_coverage = float(
            pd.to_numeric(
                pd.Series([excluded.iloc[0]["hedge_greek_solved_contract_volume_pct"]]),
                errors="coerce",
            ).iloc[0]
        )
        if pd.isna(excluded_flow) or excluded_flow.strftime("%H:%M:%S") != EXPECTED_EXCLUDED_FLOW_MINUTE_UTC:
            raise ValueError(
                f"{day}: expected the sole excluded row to be the 13:30:00 UTC flow minute; found {excluded_flow}"
            )
        if not np.isfinite(excluded_coverage) or excluded_coverage != 0.0:
            raise ValueError(
                f"{day}: expected sole excluded row coverage 0.0; found {excluded_coverage}"
            )

        rows.append(
            {
                "trading_day": day,
                "opening_rows": int(len(safe)),
                "replay_matches": int(replay.sum()),
                "eligible_ge_90pct": int(eligible.sum()),
                "excluded_lt_90pct": int(len(excluded)),
                "excluded_flow_minute": str(excluded.iloc[0]["flow_minute"]),
                "excluded_coverage": excluded_coverage,
            }
        )

    seen_path = _seen_chronology_path(data_dir)
    if not seen_path.exists():
        raise ValueError(
            "missing frozen seen-data chronology artifact: "
            f"{seen_path}; rerun the already-seen chronological-drift characterization before reveal"
        )
    seen_headers = set(pd.read_csv(seen_path, nrows=0).columns)
    if not {"trading_day", "ordinary_spearman"}.issubset(seen_headers):
        raise ValueError(
            f"seen-data chronology artifact must contain trading_day and ordinary_spearman: {seen_path}"
        )
    seen_days = tuple(pd.read_csv(seen_path, usecols=["trading_day"])["trading_day"].astype(str))
    if seen_days != SEEN_DATES:
        raise ValueError(
            "seen-data chronology dates differ from the frozen 17-session sequence; reveal aborted"
        )

    return pd.DataFrame(rows)


def _evaluate_holdout_day(data_dir: Path, day: str) -> dict[str, object]:
    raw = pd.read_csv(_raw_path(data_dir, day))
    hedge = pd.read_csv(_hedge_path(data_dir, day))
    sample = frozen_opening_sample(
        raw,
        hedge,
        min_volume_coverage=MIN_VOLUME_COVERAGE,
    )
    if len(sample) != EXPECTED_ELIGIBLE_ROWS:
        raise ValueError(
            f"{day}: expected {EXPECTED_ELIGIBLE_ROWS} complete frozen opening 15m rows at reveal; found {len(sample)}"
        )

    endpoint_b = _spearman(sample[HEDGE], sample[TARGET])
    _, endpoint_a = partial_spearman(
        sample[HEDGE],
        sample[TARGET],
        sample[[MOMENTUM, RAW]],
    )
    loo = _ordinary_loo_values(sample)
    category, same_count, same_pct = _classify(endpoint_b, loo)
    return {
        "trading_day": day,
        "observations": int(len(sample)),
        "endpoint_b_ordinary_spearman": float(endpoint_b),
        "endpoint_a_partial_momentum_raw": float(endpoint_a),
        "endpoint_b_sign": "positive" if endpoint_b > 0 else "negative" if endpoint_b < 0 else "zero",
        "endpoint_b_stability_category": category,
        "endpoint_b_loo_count": int(len(loo)),
        "endpoint_b_loo_same_sign_count": same_count,
        "endpoint_b_loo_same_sign_pct": same_pct,
        "endpoint_b_loo_min": float(np.min(loo)) if len(loo) else np.nan,
        "endpoint_b_loo_max": float(np.max(loo)) if len(loo) else np.nan,
    }


def _trend_summary(day_table: pd.DataFrame) -> dict[str, object]:
    values = pd.to_numeric(day_table["ordinary_spearman"], errors="coerce").reset_index(drop=True)
    index = pd.Series(np.arange(1, len(values) + 1, dtype=float))
    full = _spearman(index, values)
    loo: list[float] = []
    for drop in range(len(values)):
        keep = [i for i in range(len(values)) if i != drop]
        subset_index = pd.Series(np.arange(1, len(keep) + 1, dtype=float))
        subset_values = values.iloc[keep].reset_index(drop=True)
        value = _spearman(subset_index, subset_values)
        if np.isfinite(value):
            loo.append(float(value))
    array = np.asarray(loo, dtype=float)
    full_sign = int(np.sign(full)) if np.isfinite(full) else 0
    signs = np.sign(array).astype(int) if len(array) else np.asarray([], dtype=int)
    same = int(np.sum(signs == full_sign)) if full_sign and len(signs) else 0
    return {
        "combined_20_trend_spearman": float(full),
        "combined_20_trend_negative": bool(np.isfinite(full) and full < 0),
        "combined_20_trend_loo_count": int(len(array)),
        "combined_20_trend_loo_same_sign_count": same,
        "combined_20_trend_loo_same_sign_pct": (
            float(same / len(array)) if full_sign and len(array) else np.nan
        ),
        "combined_20_trend_loo_median": float(np.median(array)) if len(array) else np.nan,
        "combined_20_trend_loo_min": float(np.min(array)) if len(array) else np.nan,
        "combined_20_trend_loo_max": float(np.max(array)) if len(array) else np.nan,
        "combined_20_trend_loo_any_opposite_sign": bool(
            full_sign and len(signs) and np.any((signs != 0) & (signs == -full_sign))
        ),
    }


def _sign_run_summary(values: pd.Series) -> dict[str, object]:
    numeric = pd.to_numeric(values, errors="coerce")
    signs = [int(np.sign(value)) for value in numeric if np.isfinite(value)]
    if not signs:
        return {
            "sign_runs": 0,
            "longest_negative_run": 0,
            "longest_positive_run": 0,
            "terminal_run_sign": "none",
            "terminal_run_length": 0,
        }
    run_count = 1
    current_sign = signs[0]
    current_len = 1
    longest_negative = 1 if current_sign < 0 else 0
    longest_positive = 1 if current_sign > 0 else 0
    for sign in signs[1:]:
        if sign == current_sign:
            current_len += 1
            continue
        if current_sign < 0:
            longest_negative = max(longest_negative, current_len)
        elif current_sign > 0:
            longest_positive = max(longest_positive, current_len)
        run_count += 1
        current_sign = sign
        current_len = 1
    if current_sign < 0:
        longest_negative = max(longest_negative, current_len)
    elif current_sign > 0:
        longest_positive = max(longest_positive, current_len)
    return {
        "sign_runs": int(run_count),
        "longest_negative_run": int(longest_negative),
        "longest_positive_run": int(longest_positive),
        "terminal_run_sign": "positive" if current_sign > 0 else "negative" if current_sign < 0 else "zero",
        "terminal_run_length": int(current_len),
    }


def _rolling_medians(day_table: pd.DataFrame) -> pd.DataFrame:
    values = pd.to_numeric(day_table["ordinary_spearman"], errors="coerce")
    rows: list[dict[str, object]] = []
    for end in range(ROLLING_WINDOW - 1, len(day_table)):
        start = end - ROLLING_WINDOW + 1
        median = float(values.iloc[start : end + 1].median())
        rows.append(
            {
                "window_start": str(day_table.iloc[start]["trading_day"]),
                "window_end": str(day_table.iloc[end]["trading_day"]),
                "sessions": ROLLING_WINDOW,
                "rolling_median_ordinary_spearman": median,
                "rolling_median_sign": "positive" if median > 0 else "negative" if median < 0 else "zero",
            }
        )
    return pd.DataFrame(rows)


def _reveal(data_dir: Path) -> None:
    # Fail closed on all holdout-safe checks before loading any holdout label values.
    _safe_holdout_preflight(data_dir)

    # Compute all three holdout dates before printing any endpoint result so the
    # untouched block is revealed together rather than sequentially.
    holdout_rows = [_evaluate_holdout_day(data_dir, day) for day in HOLDOUT_DATES]
    per_day = pd.DataFrame(holdout_rows)
    if len(per_day) != len(HOLDOUT_DATES):
        raise ValueError("holdout reveal did not produce all three frozen dates")

    endpoint_values = pd.to_numeric(per_day["endpoint_b_ordinary_spearman"], errors="coerce")
    if endpoint_values.isna().any():
        raise ValueError("one or more holdout Endpoint-B values are non-finite; reveal aborted")
    holdout_median = float(endpoint_values.median())
    primary_pass = bool(holdout_median > AUGUST_REFERENCE_MEDIAN)

    sign_counts = {
        "negative_days": int((endpoint_values < 0).sum()),
        "positive_days": int((endpoint_values > 0).sum()),
        "zero_days": int((endpoint_values == 0).sum()),
        "strict_sign_stable_negative_days": int(
            (per_day["endpoint_b_stability_category"] == "strict_sign_stable_negative").sum()
        ),
        "strict_sign_stable_positive_days": int(
            (per_day["endpoint_b_stability_category"] == "strict_sign_stable_positive").sum()
        ),
        "sign_fragile_days": int(
            (per_day["endpoint_b_stability_category"] == "sign_fragile").sum()
        ),
    }

    seen = pd.read_csv(_seen_chronology_path(data_dir), usecols=["trading_day", "ordinary_spearman"])
    seen["trading_day"] = seen["trading_day"].astype(str)
    if tuple(seen["trading_day"]) != SEEN_DATES:
        raise ValueError("frozen seen-data chronology changed between preflight and reveal")

    holdout_chronology = per_day[["trading_day", "endpoint_b_ordinary_spearman"]].rename(
        columns={"endpoint_b_ordinary_spearman": "ordinary_spearman"}
    )
    holdout_chronology["trading_day"] = pd.Categorical(
        holdout_chronology["trading_day"],
        categories=CHRONOLOGICAL_HOLDOUT_DATES,
        ordered=True,
    )
    holdout_chronology = holdout_chronology.sort_values("trading_day").copy()
    holdout_chronology["trading_day"] = holdout_chronology["trading_day"].astype(str)
    combined = pd.concat([holdout_chronology, seen], ignore_index=True, sort=False)
    if tuple(combined["trading_day"]) != CHRONOLOGICAL_HOLDOUT_DATES + SEEN_DATES:
        raise ValueError("combined 20-session chronology is not in the frozen chronological order")
    combined.insert(0, "chronological_index", np.arange(1, len(combined) + 1, dtype=int))

    trend = _trend_summary(combined)
    runs = _sign_run_summary(combined["ordinary_spearman"])
    rolling = _rolling_medians(combined)
    combined_negative = bool(trend["combined_20_trend_negative"])
    overall_support = bool(primary_pass and combined_negative)

    summary = pd.DataFrame(
        [
            {
                "holdout_days": 3,
                "holdout_median_endpoint_b": holdout_median,
                "august_reference_median": AUGUST_REFERENCE_MEDIAN,
                "primary_condition_holdout_median_gt_reference": primary_pass,
                **sign_counts,
                **trend,
                **runs,
                "frozen_temporal_extension_support": overall_support,
                "frozen_interpretation": (
                    "temporal-extension support"
                    if overall_support
                    else "temporal-extension failure/weakening"
                ),
            }
        ]
    )

    data_dir.mkdir(parents=True, exist_ok=True)
    by_day_output = data_dir / "gexy_spxw_temporal_extension_holdout_by_day.csv"
    summary_output = data_dir / "gexy_spxw_temporal_extension_holdout_summary.csv"
    combined_output = data_dir / "gexy_spxw_temporal_extension_combined20.csv"
    rolling_output = data_dir / "gexy_spxw_temporal_extension_combined20_rolling5.csv"
    per_day.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)
    combined.to_csv(combined_output, index=False)
    rolling.to_csv(rolling_output, index=False)

    print("GEXY TEMPORAL-EXTENSION HOLDOUT — FROZEN THREE-DATE REVEAL")
    print(f"DATES (FROZEN REVEAL ORDER): {','.join(HOLDOUT_DATES)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print(f"HORIZON: {FROZEN_HORIZON_MINUTES} minutes only")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {MIN_VOLUME_COVERAGE:.0%}")
    print("ENDPOINT B: ordinary Spearman(hedge_delta_units, forward_return_15m_bps)")
    print("ENDPOINT A: historical two-control partial Spearman; continuity only")
    print("NO P-VALUE / INDEPENDENCE CLAIM AUTHORIZED")

    display = [
        "trading_day",
        "observations",
        "endpoint_b_ordinary_spearman",
        "endpoint_b_sign",
        "endpoint_b_stability_category",
        "endpoint_b_loo_same_sign_count",
        "endpoint_b_loo_count",
        "endpoint_b_loo_same_sign_pct",
        "endpoint_b_loo_min",
        "endpoint_b_loo_max",
        "endpoint_a_partial_momentum_raw",
    ]
    print("\nTHREE UNTOUCHED ENDPOINTS — REVEALED TOGETHER")
    print(per_day[display].to_string(index=False))
    print("\nFROZEN TEMPORAL-EXTENSION ADJUDICATION")
    print(summary.to_string(index=False))
    print("\nCOMBINED 20-SESSION CHRONOLOGY")
    print(combined.to_string(index=False))
    print("\nFIXED 5-SESSION ROLLING MEDIANS")
    print(rolling.to_string(index=False))
    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print(f"COMBINED-20 CSV: {combined_output}")
    print(f"ROLLING-5 CSV: {rolling_output}")
    print("NO PAID DATA REQUESTS: this validator reads only existing local feature/summary CSVs.")
    print("INTERPRETATION LIMIT: hedge_delta_units is an inferred liquidity-provider/dealer-hedge proxy; this descriptive holdout does not establish causality, stationarity, or a production trading edge.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Safeguard and reveal the frozen GEXY three-date temporal-extension holdout. "
            "Default mode is holdout-safe preflight and does not read forward-return label values. "
            "Use --reveal only for the dedicated all-three-date Endpoint-B reveal."
        )
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--reveal",
        action="store_true",
        help="explicitly reveal all three frozen holdout Endpoint-B values together",
    )
    args = parser.parse_args()

    try:
        if args.reveal:
            _reveal(args.data_dir)
            return
        preflight = _safe_holdout_preflight(args.data_dir)
    except ValueError as exc:
        raise SystemExit(f"TEMPORAL-EXTENSION HOLDOUT ABORTED: {exc}") from exc

    print("GEXY TEMPORAL-EXTENSION HOLDOUT — SAFE PREFLIGHT")
    print(f"DATES LOCKED: {','.join(HOLDOUT_DATES)}")
    print("WINDOW LOCKED: 09:30-10:00 America/New_York only")
    print(f"HORIZON LOCKED: {FROZEN_HORIZON_MINUTES} minutes only")
    print(f"GREEK-VOLUME COVERAGE LOCKED: {MIN_VOLUME_COVERAGE:.0%}")
    print(f"AUGUST REFERENCE MEDIAN LOCKED: {AUGUST_REFERENCE_MEDIAN:.6f}")
    print("TARGET LOCKED: forward_return_15m_bps")
    print("SIGNAL LOCKED: hedge_delta_units")
    print("\nHOLDOUT-SAFE PREPARATION CHECK")
    print(preflight.to_string(index=False))
    print("\nPREFLIGHT PASS: all frozen preparation facts and the 17-session seen chronology artifact match expectations.")
    print("HOLDOUT SAFETY: no forward-return label values or Endpoint-B values were read or displayed in preflight mode.")
    print("NEXT ACTION WHEN AUTHORIZED: rerun this exact validator with --reveal; it will reveal all three dates together.")
    print("NO PAID DATA REQUESTS: reads existing local files only.")


if __name__ == "__main__":
    main()
