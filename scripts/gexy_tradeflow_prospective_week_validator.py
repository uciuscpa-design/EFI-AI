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
PROSPECTIVE_DATES = (
    "2026-08-17",
    "2026-08-18",
    "2026-08-19",
    "2026-08-20",
    "2026-08-21",
)
BASE_20_DATES = (
    "2026-07-17",
    "2026-07-20",
    "2026-07-21",
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
MIN_CORRELATION_ROWS = 3


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def _base_20_path(data_dir: Path) -> Path:
    return data_dir / "gexy_spxw_temporal_extension_combined20.csv"


def _truthy(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _validate_base_20(data_dir: Path, *, read_values: bool) -> pd.DataFrame | None:
    path = _base_20_path(data_dir)
    if not path.exists():
        raise ValueError(
            "missing official 20-session chronology artifact: "
            f"{path}; rerun the already-completed temporal-extension reveal before prospective validation"
        )
    headers = set(pd.read_csv(path, nrows=0).columns)
    required = {"trading_day", "ordinary_spearman"}
    missing = sorted(required.difference(headers))
    if missing:
        raise ValueError(
            f"official 20-session chronology artifact missing columns: {', '.join(missing)}"
        )
    days = tuple(pd.read_csv(path, usecols=["trading_day"])["trading_day"].astype(str))
    if days != BASE_20_DATES:
        raise ValueError(
            "official 20-session chronology dates differ from the frozen sequence; prospective validation aborted"
        )
    if not read_values:
        return None
    base = pd.read_csv(path, usecols=["trading_day", "ordinary_spearman"])
    base["trading_day"] = base["trading_day"].astype(str)
    values = pd.to_numeric(base["ordinary_spearman"], errors="coerce")
    if values.isna().any():
        raise ValueError(
            "official 20-session chronology contains non-finite ordinary_spearman values"
        )
    base["ordinary_spearman"] = values
    return base


def _self_check(data_dir: Path) -> pd.DataFrame:
    _validate_base_20(data_dir, read_values=False)
    rows: list[dict[str, object]] = []
    for day in PROSPECTIVE_DATES:
        rows.append(
            {
                "trading_day": day,
                "raw_feature_file_present": _raw_path(data_dir, day).exists(),
                "hedge_feature_file_present": _hedge_path(data_dir, day).exists(),
            }
        )
    return pd.DataFrame(rows)


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
    if np.all(loo_signs == sign) and sign > 0:
        return "strict_sign_stable_positive", same_count, same_pct
    if np.all(loo_signs == sign) and sign < 0:
        return "strict_sign_stable_negative", same_count, same_pct
    return "sign_fragile", same_count, same_pct


def _safe_prospective_preflight(data_dir: Path) -> pd.DataFrame:
    _validate_base_20(data_dir, read_values=False)
    rows: list[dict[str, object]] = []

    for day in PROSPECTIVE_DATES:
        raw_path = _raw_path(data_dir, day)
        hedge_path = _hedge_path(data_dir, day)
        if not raw_path.exists():
            raise ValueError(f"{day}: missing raw causal trade-flow feature CSV: {raw_path}")
        if not hedge_path.exists():
            raise ValueError(f"{day}: missing hedge-flow feature CSV: {hedge_path}")

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

        # Prospective-safe read: never load forward-return label values here.
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

        if len(safe) != EXPECTED_OPENING_ROWS:
            raise ValueError(
                f"{day}: expected {EXPECTED_OPENING_ROWS} opening rows; found {len(safe)}"
            )
        if int(replay.sum()) != EXPECTED_OPENING_ROWS:
            raise ValueError(
                f"{day}: expected {EXPECTED_OPENING_ROWS}/{EXPECTED_OPENING_ROWS} replay matches; "
                f"found {int(replay.sum())}/{len(safe)}"
            )
        if coverage.loc[replay].isna().any():
            raise ValueError(
                f"{day}: one or more replay-matched opening rows have non-numeric Greek-volume coverage"
            )

        eligible = replay & (coverage >= MIN_VOLUME_COVERAGE)
        excluded = replay & (coverage < MIN_VOLUME_COVERAGE)
        eligible_count = int(eligible.sum())
        if eligible_count < MIN_CORRELATION_ROWS:
            raise ValueError(
                f"{day}: only {eligible_count} opening rows meet the frozen >=90% coverage rule; "
                f"at least {MIN_CORRELATION_ROWS} are required to compute the frozen correlation"
            )

        rows.append(
            {
                "trading_day": day,
                "opening_rows": int(len(safe)),
                "replay_matches": int(replay.sum()),
                "eligible_ge_90pct": eligible_count,
                "excluded_lt_90pct": int(excluded.sum()),
                "min_eligible_coverage": float(coverage.loc[eligible].min()),
                "median_eligible_coverage": float(coverage.loc[eligible].median()),
            }
        )

    return pd.DataFrame(rows)


def _evaluate_prospective_day(
    data_dir: Path,
    day: str,
    expected_eligible_rows: int,
) -> dict[str, object]:
    raw = pd.read_csv(_raw_path(data_dir, day))
    hedge = pd.read_csv(_hedge_path(data_dir, day))
    sample = frozen_opening_sample(raw, hedge, min_volume_coverage=MIN_VOLUME_COVERAGE)
    if len(sample) != expected_eligible_rows:
        raise ValueError(
            f"{day}: preflight found {expected_eligible_rows} eligible rows but reveal sample has "
            f"{len(sample)} complete frozen opening 15m rows; prospective reveal aborted"
        )

    endpoint_b = _spearman(sample[HEDGE], sample[TARGET])
    if not np.isfinite(endpoint_b):
        raise ValueError(f"{day}: Endpoint B is non-finite; prospective reveal aborted")

    _, endpoint_a = partial_spearman(
        sample[HEDGE], sample[TARGET], sample[[MOMENTUM, RAW]]
    )
    loo = _ordinary_loo_values(sample)
    category, same_count, same_pct = _classify(float(endpoint_b), loo)
    return {
        "trading_day": day,
        "observations": int(len(sample)),
        "endpoint_b_ordinary_spearman": float(endpoint_b),
        "endpoint_b_sign": "positive" if endpoint_b > 0 else "negative" if endpoint_b < 0 else "zero",
        "endpoint_b_stability_category": category,
        "endpoint_b_loo_count": int(len(loo)),
        "endpoint_b_loo_same_sign_count": same_count,
        "endpoint_b_loo_same_sign_pct": same_pct,
        "endpoint_b_loo_min": float(np.min(loo)) if len(loo) else np.nan,
        "endpoint_b_loo_max": float(np.max(loo)) if len(loo) else np.nan,
        "endpoint_a_partial_momentum_raw": float(endpoint_a) if np.isfinite(endpoint_a) else np.nan,
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
        "combined_25_trend_spearman": float(full),
        "combined_25_trend_sign": "positive" if full > 0 else "negative" if full < 0 else "zero",
        "combined_25_trend_loo_count": int(len(array)),
        "combined_25_trend_loo_same_sign_count": same,
        "combined_25_trend_loo_same_sign_pct": float(same / len(array)) if full_sign and len(array) else np.nan,
        "combined_25_trend_loo_median": float(np.median(array)) if len(array) else np.nan,
        "combined_25_trend_loo_min": float(np.min(array)) if len(array) else np.nan,
        "combined_25_trend_loo_max": float(np.max(array)) if len(array) else np.nan,
        "combined_25_trend_loo_any_opposite_sign": bool(
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


def _magnitude_classification(median: float) -> str:
    if median < AUGUST_REFERENCE_MEDIAN:
        return "more_negative_than_prior_august"
    if median < 0:
        return "similar_or_weaker_negative"
    return "nonnegative_block"


def _reveal(data_dir: Path) -> None:
    preflight = _safe_prospective_preflight(data_dir)
    eligible_by_day = {
        str(row["trading_day"]): int(row["eligible_ge_90pct"])
        for _, row in preflight.iterrows()
    }

    # Compute all five sessions before printing any future endpoint result.
    prospective_rows = [
        _evaluate_prospective_day(data_dir, day, eligible_by_day[day])
        for day in PROSPECTIVE_DATES
    ]
    per_day = pd.DataFrame(prospective_rows)
    if tuple(per_day["trading_day"].astype(str)) != PROSPECTIVE_DATES:
        raise ValueError("prospective reveal did not produce all five dates in frozen order")

    endpoint_values = pd.to_numeric(per_day["endpoint_b_ordinary_spearman"], errors="coerce")
    if endpoint_values.isna().any():
        raise ValueError("one or more prospective Endpoint-B values are non-finite")
    prospective_median = float(endpoint_values.median())
    primary_pass = bool(prospective_median < 0)
    magnitude = _magnitude_classification(prospective_median)

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

    base = _validate_base_20(data_dir, read_values=True)
    assert base is not None
    prospective_chronology = per_day[
        ["trading_day", "endpoint_b_ordinary_spearman"]
    ].rename(columns={"endpoint_b_ordinary_spearman": "ordinary_spearman"})
    prospective_chronology["trading_day"] = prospective_chronology["trading_day"].astype(str)
    combined = pd.concat([base, prospective_chronology], ignore_index=True, sort=False)
    if tuple(combined["trading_day"].astype(str)) != BASE_20_DATES + PROSPECTIVE_DATES:
        raise ValueError("combined 25-session chronology is not in frozen chronological order")
    combined.insert(0, "chronological_index", np.arange(1, len(combined) + 1, dtype=int))

    trend = _trend_summary(combined)
    runs = _sign_run_summary(combined["ordinary_spearman"])
    rolling = _rolling_medians(combined)
    summary = pd.DataFrame(
        [
            {
                "prospective_days": len(PROSPECTIVE_DATES),
                "prospective_median_endpoint_b": prospective_median,
                "primary_condition_median_lt_zero": primary_pass,
                "august_reference_median": AUGUST_REFERENCE_MEDIAN,
                "magnitude_classification": magnitude,
                **sign_counts,
                **trend,
                **runs,
                "frozen_prospective_persistence_support": primary_pass,
                "frozen_interpretation": (
                    "prospective persistence support"
                    if primary_pass
                    else "prospective persistence failure/weakening"
                ),
            }
        ]
    )

    data_dir.mkdir(parents=True, exist_ok=True)
    by_day_output = data_dir / "gexy_spxw_prospective_2026-08-17_2026-08-21_by_day.csv"
    summary_output = data_dir / "gexy_spxw_prospective_2026-08-17_2026-08-21_summary.csv"
    combined_output = data_dir / "gexy_spxw_prospective_combined25.csv"
    rolling_output = data_dir / "gexy_spxw_prospective_combined25_rolling5.csv"
    per_day.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)
    combined.to_csv(combined_output, index=False)
    rolling.to_csv(rolling_output, index=False)

    print("GEXY PROSPECTIVE REPLICATION — FROZEN FIVE-DATE REVEAL")
    print(f"DATES (FROZEN ORDER): {','.join(PROSPECTIVE_DATES)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print(f"HORIZON: {FROZEN_HORIZON_MINUTES} minutes only")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {MIN_VOLUME_COVERAGE:.0%}")
    print("ENDPOINT B: ordinary Spearman(hedge_delta_units, forward_return_15m_bps)")
    print("PRIMARY CONDITION: five-day median Endpoint B < 0")
    print(f"SECONDARY MAGNITUDE REFERENCE: prior August median {AUGUST_REFERENCE_MEDIAN:.6f}")
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
    print("\nFIVE PROSPECTIVE ENDPOINTS — REVEALED TOGETHER")
    print(per_day[display].to_string(index=False))
    print("\nFROZEN PROSPECTIVE ADJUDICATION")
    print(summary.to_string(index=False))
    print("\nCOMBINED 25-SESSION CHRONOLOGY")
    print(combined.to_string(index=False))
    print("\nFIXED 5-SESSION ROLLING MEDIANS")
    print(rolling.to_string(index=False))
    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print(f"COMBINED-25 CSV: {combined_output}")
    print(f"ROLLING-5 CSV: {rolling_output}")
    print("NO PAID DATA REQUESTS: this validator reads only existing local feature/summary CSVs.")
    print(
        "INTERPRETATION LIMIT: hedge_delta_units is an inferred liquidity-provider/dealer-hedge "
        "proxy; this prospective descriptive replication does not establish causality, "
        "stationarity, independence, or a production trading edge."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Safeguard and reveal the frozen GEXY 2026-08-17 through 2026-08-21 prospective "
            "replication. Default mode is prospective-safe preflight and does not read "
            "forward-return label values. Use --self-check before future files exist, and "
            "--reveal only after all five dates are fully prepared."
        )
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--self-check",
        action="store_true",
        help=(
            "verify frozen constants/base chronology and report future-file presence "
            "without reading future feature contents"
        ),
    )
    mode.add_argument(
        "--reveal",
        action="store_true",
        help="explicitly reveal all five frozen prospective Endpoint-B values together",
    )
    args = parser.parse_args()

    try:
        if args.self_check:
            status = _self_check(args.data_dir)
            print("GEXY PROSPECTIVE REPLICATION — VALIDATOR SELF-CHECK")
            print(f"DATES LOCKED: {','.join(PROSPECTIVE_DATES)}")
            print("WINDOW LOCKED: 09:30-10:00 America/New_York only")
            print(f"HORIZON LOCKED: {FROZEN_HORIZON_MINUTES} minutes only")
            print(f"GREEK-VOLUME COVERAGE LOCKED: {MIN_VOLUME_COVERAGE:.0%}")
            print("PRIMARY CONDITION LOCKED: five-day median Endpoint B < 0")
            print(f"SECONDARY AUGUST REFERENCE LOCKED: {AUGUST_REFERENCE_MEDIAN:.6f}")
            print("TARGET LOCKED: forward_return_15m_bps")
            print("SIGNAL LOCKED: hedge_delta_units")
            print("\nFUTURE FILE PRESENCE ONLY")
            print(status.to_string(index=False))
            print("\nSELF-CHECK PASS: official 20-session base chronology matches the frozen sequence.")
            print(
                "PROSPECTIVE SAFETY: no future feature contents, forward-return label values, "
                "or future Endpoint-B values were read."
            )
            print("NO PAID DATA REQUESTS: local file-presence/base-date checks only.")
            return

        if args.reveal:
            _reveal(args.data_dir)
            return

        preflight = _safe_prospective_preflight(args.data_dir)
    except ValueError as exc:
        raise SystemExit(f"PROSPECTIVE REPLICATION ABORTED: {exc}") from exc

    print("GEXY PROSPECTIVE REPLICATION — SAFE PREFLIGHT")
    print(f"DATES LOCKED: {','.join(PROSPECTIVE_DATES)}")
    print("WINDOW LOCKED: 09:30-10:00 America/New_York only")
    print(f"HORIZON LOCKED: {FROZEN_HORIZON_MINUTES} minutes only")
    print(f"GREEK-VOLUME COVERAGE LOCKED: {MIN_VOLUME_COVERAGE:.0%}")
    print("PRIMARY CONDITION LOCKED: five-day median Endpoint B < 0")
    print(f"SECONDARY AUGUST REFERENCE LOCKED: {AUGUST_REFERENCE_MEDIAN:.6f}")
    print("TARGET LOCKED: forward_return_15m_bps")
    print("SIGNAL LOCKED: hedge_delta_units")
    print("\nPROSPECTIVE-SAFE PREPARATION CHECK")
    print(preflight.to_string(index=False))
    print(
        "\nPREFLIGHT PASS: all five frozen dates are fully prepared and the official "
        "20-session base chronology matches expectations."
    )
    print(
        "PROSPECTIVE SAFETY: no forward-return label values or prospective Endpoint-B "
        "values were read or displayed in preflight mode."
    )
    print(
        "NEXT ACTION WHEN AUTHORIZED: rerun this exact validator with --reveal; "
        "it will compute and reveal all five dates together."
    )
    print("NO PAID DATA REQUESTS: reads existing local files only.")


if __name__ == "__main__":
    main()
