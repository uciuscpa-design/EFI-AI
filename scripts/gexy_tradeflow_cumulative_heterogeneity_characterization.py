from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_batch4_heterogeneity import (
    HEDGE,
    TARGET,
    _spearman,
    audit_day,
    frozen_opening_sample,
)


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
MIN_VOLUME_COVERAGE = 0.90
FROZEN_DATES = (
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
RESERVED_HOLDOUT_DATES = ("2026-07-21", "2026-07-20", "2026-07-17")


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


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


def _aggregate(result: pd.DataFrame) -> pd.DataFrame:
    values = pd.to_numeric(result["ordinary_spearman"], errors="coerce").dropna()
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    return pd.DataFrame(
        [
            {
                "days": int(len(values)),
                "negative_days": int((values < 0).sum()),
                "positive_days": int((values > 0).sum()),
                "zero_days": int((values == 0).sum()),
                "strict_sign_stable_negative_days": int(
                    (result["ordinary_stability_category"] == "strict_sign_stable_negative").sum()
                ),
                "strict_sign_stable_positive_days": int(
                    (result["ordinary_stability_category"] == "strict_sign_stable_positive").sum()
                ),
                "sign_fragile_days": int(
                    (result["ordinary_stability_category"] == "sign_fragile").sum()
                ),
                "ordinary_loo_same_sign_ge_80pct_days": int(
                    (pd.to_numeric(result["ordinary_loo_same_sign_pct"], errors="coerce") >= 0.80).sum()
                ),
                "median_ordinary_spearman": float(values.median()),
                "min_ordinary_spearman": float(values.min()),
                "max_ordinary_spearman": float(values.max()),
                "std_ordinary_spearman": float(values.std(ddof=1)),
                "q1_ordinary_spearman": q1,
                "q3_ordinary_spearman": q3,
                "iqr_ordinary_spearman": q3 - q1,
                "median_ordinary_largest_abs_contribution_share": float(
                    pd.to_numeric(
                        result["ordinary_largest_abs_contribution_share"], errors="coerce"
                    ).median()
                ),
                "median_ordinary_top3_abs_contribution_share": float(
                    pd.to_numeric(
                        result["ordinary_top3_abs_contribution_share"], errors="coerce"
                    ).median()
                ),
                "median_ordinary_top5_abs_contribution_share": float(
                    pd.to_numeric(
                        result["ordinary_top5_abs_contribution_share"], errors="coerce"
                    ).median()
                ),
            }
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Characterize frozen GEXY opening 15m heterogeneity across exactly 17 already-seen dates. "
            "Uses the existing leave-one-minute-out audit math, creates no predictor, reads no reserved "
            "holdout date, and makes no market-data request."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    missing: list[str] = []
    for day in FROZEN_DATES:
        for path in (_raw_path(args.data_dir, day), _hedge_path(args.data_dir, day)):
            if not path.exists():
                missing.append(str(path))
    if missing:
        raise SystemExit(
            "CUMULATIVE HETEROGENEITY CHARACTERIZATION ABORTED: missing frozen local inputs: "
            + ", ".join(missing)
        )

    rows: list[dict[str, object]] = []
    for day in FROZEN_DATES:
        raw = pd.read_csv(_raw_path(args.data_dir, day))
        hedge = pd.read_csv(_hedge_path(args.data_dir, day))
        row = audit_day(
            raw,
            hedge,
            trading_day=day,
            min_volume_coverage=MIN_VOLUME_COVERAGE,
        )
        sample = frozen_opening_sample(
            raw,
            hedge,
            min_volume_coverage=MIN_VOLUME_COVERAGE,
        )
        loo = _ordinary_loo_values(sample)
        category, same_count, same_pct = _classify(float(row["ordinary_spearman"]), loo)
        row["ordinary_stability_category"] = category
        row["ordinary_loo_same_sign_count"] = same_count
        row["ordinary_loo_same_sign_pct"] = same_pct
        rows.append(row)

    result = pd.DataFrame(rows)
    summary = _aggregate(result)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    by_day_output = args.data_dir / "gexy_spxw_cumulative_heterogeneity_characterization_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_cumulative_heterogeneity_characterization_summary.csv"
    result.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)

    print("GEXY CUMULATIVE OPENING HETEROGENEITY CHARACTERIZATION — 17 SEEN DAYS")
    print(f"DATES: {','.join(FROZEN_DATES)}")
    print(f"RESERVED HOLDOUT NOT READ: {','.join(RESERVED_HOLDOUT_DATES)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print("HORIZON: 15 minutes only")
    print("MIN CLASSIFIED-VOLUME GREEK COVERAGE: 90%")
    print("STATUS: descriptive influence characterization only; no predictor or regime classifier")

    display = [
        "trading_day",
        "observations",
        "ordinary_spearman",
        "ordinary_stability_category",
        "ordinary_loo_same_sign_count",
        "ordinary_loo_same_sign_pct",
        "ordinary_loo_min",
        "ordinary_loo_max",
        "ordinary_loo_max_abs_change",
        "ordinary_largest_abs_contribution_share",
        "ordinary_top3_abs_contribution_share",
        "ordinary_top5_abs_contribution_share",
        "partial_controlling_both",
        "rank_hedge_r2_from_both_controls",
        "rank_target_r2_from_both_controls",
    ]
    print("\nDAY-BY-DAY CHARACTERIZATION")
    print(result[display].to_string(index=False))
    print("\nFROZEN AGGREGATE SUMMARY")
    print(summary.to_string(index=False))
    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print("NO PAID DATA REQUESTS: reads existing local development feature CSVs only.")
    print("NO HOLDOUT INSPECTION: reserved dates are not read.")
    print("INTERPRETATION LIMIT: LOO stability is an influence diagnostic, not an independence-based significance test or production edge.")


if __name__ == "__main__":
    main()
