from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_batch4_heterogeneity import audit_day, frozen_opening_sample
from scripts.gexy_tradeflow_cumulative_heterogeneity_characterization import (
    _classify,
    _ordinary_loo_values,
)


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
MIN_VOLUME_COVERAGE = 0.90
CHRONOLOGICAL_DATES = (
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
RESERVED_HOLDOUT_DATES = ("2026-07-21", "2026-07-20", "2026-07-17")
ROLLING_WINDOW = 5


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def _spearman(x: pd.Series, y: pd.Series) -> float:
    frame = pd.DataFrame(
        {"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")}
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return float("nan")
    return float(
        frame["x"].rank(method="average").corr(
            frame["y"].rank(method="average"), method="pearson"
        )
    )


def _trend_summary(day_table: pd.DataFrame) -> dict[str, object]:
    index = pd.Series(np.arange(1, len(day_table) + 1, dtype=float))
    values = pd.to_numeric(day_table["ordinary_spearman"], errors="coerce").reset_index(drop=True)
    full = _spearman(index, values)
    loo: list[float] = []
    for drop in range(len(day_table)):
        keep = [i for i in range(len(day_table)) if i != drop]
        subset_index = pd.Series(np.arange(1, len(keep) + 1, dtype=float))
        subset_values = values.iloc[keep].reset_index(drop=True)
        value = _spearman(subset_index, subset_values)
        if np.isfinite(value):
            loo.append(float(value))
    array = np.asarray(loo, dtype=float)
    full_sign = int(np.sign(full)) if np.isfinite(full) else 0
    if len(array):
        signs = np.sign(array).astype(int)
        same = int(np.sum(signs == full_sign)) if full_sign else 0
        opposite = bool(full_sign and np.any((signs != 0) & (signs == -full_sign)))
        return {
            "trend_spearman": float(full),
            "trend_loo_count": int(len(array)),
            "trend_loo_same_sign_count": same,
            "trend_loo_same_sign_pct": float(same / len(array)) if full_sign else float("nan"),
            "trend_loo_median": float(np.median(array)),
            "trend_loo_min": float(np.min(array)),
            "trend_loo_max": float(np.max(array)),
            "trend_loo_any_opposite_sign": opposite,
        }
    return {
        "trend_spearman": float(full),
        "trend_loo_count": 0,
        "trend_loo_same_sign_count": 0,
        "trend_loo_same_sign_pct": float("nan"),
        "trend_loo_median": float("nan"),
        "trend_loo_min": float("nan"),
        "trend_loo_max": float("nan"),
        "trend_loo_any_opposite_sign": False,
    }


def _rolling_medians(day_table: pd.DataFrame) -> pd.DataFrame:
    values = pd.to_numeric(day_table["ordinary_spearman"], errors="coerce")
    rows: list[dict[str, object]] = []
    for end in range(ROLLING_WINDOW - 1, len(day_table)):
        start = end - ROLLING_WINDOW + 1
        window_values = values.iloc[start : end + 1]
        median = float(window_values.median())
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


def _sign_run_summary(values: pd.Series) -> dict[str, object]:
    numeric = pd.to_numeric(values, errors="coerce")
    signs = [int(np.sign(v)) for v in numeric if np.isfinite(v)]
    if not signs:
        return {
            "sign_runs": 0,
            "longest_negative_run": 0,
            "longest_positive_run": 0,
            "terminal_run_sign": "none",
            "terminal_run_length": 0,
        }
    run_count = 1
    longest_negative = 1 if signs[0] < 0 else 0
    longest_positive = 1 if signs[0] > 0 else 0
    current_sign = signs[0]
    current_len = 1
    for sign in signs[1:]:
        if sign == current_sign:
            current_len += 1
        else:
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
    terminal_sign = "positive" if current_sign > 0 else "negative" if current_sign < 0 else "zero"
    return {
        "sign_runs": int(run_count),
        "longest_negative_run": int(longest_negative),
        "longest_positive_run": int(longest_positive),
        "terminal_run_sign": terminal_sign,
        "terminal_run_length": int(current_len),
    }


def _month_summary(day_table: pd.DataFrame) -> pd.DataFrame:
    working = day_table.copy()
    working["month"] = pd.to_datetime(working["trading_day"], errors="coerce").dt.strftime("%Y-%m")
    rows: list[dict[str, object]] = []
    for month, group in working.groupby("month", sort=True):
        values = pd.to_numeric(group["ordinary_spearman"], errors="coerce").dropna()
        rows.append(
            {
                "month": month,
                "days": int(len(values)),
                "negative_days": int((values < 0).sum()),
                "positive_days": int((values > 0).sum()),
                "zero_days": int((values == 0).sum()),
                "strict_sign_stable_negative_days": int(
                    (group["ordinary_stability_category"] == "strict_sign_stable_negative").sum()
                ),
                "strict_sign_stable_positive_days": int(
                    (group["ordinary_stability_category"] == "strict_sign_stable_positive").sum()
                ),
                "sign_fragile_days": int(
                    (group["ordinary_stability_category"] == "sign_fragile").sum()
                ),
                "median_ordinary_spearman": float(values.median()),
                "min_ordinary_spearman": float(values.min()),
                "max_ordinary_spearman": float(values.max()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Post-hoc descriptive GEXY chronological-drift characterization across exactly 17 already-seen dates.\n"
            "Uses ordinal-time Spearman, fixed 5-session rolling medians, sign runs, and a July/August descriptive partition.\n"
            "Creates no predictor, reads no reserved holdout date, and makes no market-data request."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    missing: list[str] = []
    for day in CHRONOLOGICAL_DATES:
        for path in (_raw_path(args.data_dir, day), _hedge_path(args.data_dir, day)):
            if not path.exists():
                missing.append(str(path))
    if missing:
        raise SystemExit(
            "CHRONOLOGICAL DRIFT CHARACTERIZATION ABORTED: missing frozen local inputs: "
            + ", ".join(missing)
        )

    rows: list[dict[str, object]] = []
    for ordinal, day in enumerate(CHRONOLOGICAL_DATES, start=1):
        raw = pd.read_csv(_raw_path(args.data_dir, day))
        hedge = pd.read_csv(_hedge_path(args.data_dir, day))
        row = audit_day(raw, hedge, trading_day=day, min_volume_coverage=MIN_VOLUME_COVERAGE)
        sample = frozen_opening_sample(raw, hedge, min_volume_coverage=MIN_VOLUME_COVERAGE)
        loo = _ordinary_loo_values(sample)
        category, same_count, same_pct = _classify(float(row["ordinary_spearman"]), loo)
        rows.append(
            {
                "chronological_index": ordinal,
                "trading_day": day,
                "ordinary_spearman": float(row["ordinary_spearman"]),
                "ordinary_stability_category": category,
                "ordinary_loo_same_sign_count": same_count,
                "ordinary_loo_same_sign_pct": same_pct,
            }
        )

    day_table = pd.DataFrame(rows)
    trend = _trend_summary(day_table)
    runs = _sign_run_summary(day_table["ordinary_spearman"])
    summary = pd.DataFrame([{**trend, **runs}])
    rolling = _rolling_medians(day_table)
    months = _month_summary(day_table)

    args.data_dir.mkdir(parents=True, exist_ok=True)
    day_output = args.data_dir / "gexy_spxw_chronological_drift_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_chronological_drift_summary.csv"
    rolling_output = args.data_dir / "gexy_spxw_chronological_drift_rolling5.csv"
    month_output = args.data_dir / "gexy_spxw_chronological_drift_months.csv"
    day_table.to_csv(day_output, index=False)
    summary.to_csv(summary_output, index=False)
    rolling.to_csv(rolling_output, index=False)
    months.to_csv(month_output, index=False)

    print("GEXY CHRONOLOGICAL DRIFT CHARACTERIZATION — POST-HOC DESCRIPTIVE")
    print(f"DATES OLDEST->NEWEST: {','.join(CHRONOLOGICAL_DATES)}")
    print(f"RESERVED HOLDOUT NOT READ: {','.join(RESERVED_HOLDOUT_DATES)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print("HORIZON: 15 minutes only")
    print("MIN CLASSIFIED-VOLUME GREEK COVERAGE: 90%")
    print("STATUS: seen-data nonstationarity characterization only; no predictor or calendar rule")

    print("\nDAY-BY-DAY CHRONOLOGY")
    print(day_table.to_string(index=False))
    print("\nORDINAL-TIME / RUN SUMMARY")
    print(summary.to_string(index=False))
    print("\nFIXED 5-SESSION ROLLING MEDIANS")
    print(rolling.to_string(index=False))
    print("\nPOST-HOC CALENDAR-MONTH DESCRIPTION")
    print(months.to_string(index=False))

    print(f"\nBY-DAY CSV: {day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print(f"ROLLING CSV: {rolling_output}")
    print(f"MONTH CSV: {month_output}")
    print("NO PAID DATA REQUESTS: reads existing local development feature CSVs only.")
    print("NO HOLDOUT INSPECTION: reserved dates are not read.")
    print("INTERPRETATION LIMIT: post-hoc chronology does not establish a persistent regime, causality, or production edge.")


if __name__ == "__main__":
    main()
