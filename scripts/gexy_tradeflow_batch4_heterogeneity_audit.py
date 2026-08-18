from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_batch4_heterogeneity import audit_day


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_MIN_VOLUME_COVERAGE = 0.90


def _parse_dates(value: str) -> tuple[str, ...]:
    dates: list[str] = []
    seen: set[str] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            parsed = pd.Timestamp(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates") from exc
        if parsed.strftime("%Y-%m-%d") != item:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates")
        if item not in seen:
            seen.add(item)
            dates.append(item)
    if not dates:
        raise argparse.ArgumentTypeError("--dates must contain at least one YYYY-MM-DD date")
    return tuple(dates)


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen post-validation GEXY Batch-4 opening heterogeneity audit. "
            "The audit is 15m only, uses only hedge/raw/momentum/target variables, and measures "
            "rank residualization plus leave-one-minute-out and contribution concentration. "
            "It makes no market-data request and cannot change the Batch-4 verdict."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--min-volume-coverage",
        type=float,
        default=DEFAULT_MIN_VOLUME_COVERAGE,
        help="frozen Batch-4 classified-volume Greek coverage floor; default: 0.90",
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    if not 0.0 <= args.min_volume_coverage <= 1.0:
        parser.error("--min-volume-coverage must be between 0 and 1")

    rows: list[dict[str, object]] = []
    for day in args.dates:
        raw_path = _raw_path(args.data_dir, day)
        hedge_path = _hedge_path(args.data_dir, day)
        if not raw_path.exists():
            raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
        if not hedge_path.exists():
            raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")
        try:
            rows.append(
                audit_day(
                    pd.read_csv(raw_path),
                    pd.read_csv(hedge_path),
                    trading_day=day,
                    min_volume_coverage=args.min_volume_coverage,
                )
            )
        except ValueError as exc:
            raise SystemExit(f"{day}: {exc}") from exc

    result = pd.DataFrame(rows)
    output = args.data_dir / "gexy_spxw_tradeflow_batch4_heterogeneity_audit.csv"
    args.data_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)

    print("GEXY BATCH-4 OPENING HETEROGENEITY AUDIT — FROZEN POST-VALIDATION DIAGNOSTIC")
    print(f"DATES: {','.join(args.dates)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print("HORIZON: 15 minutes only")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("VARIABLES ONLY: hedge_delta_units, flow_net_signed_contracts, backward_return_1m_bps, forward_return_15m_bps")
    print("STATUS: post-validation diagnostic; official Batch-4 verdict is unchanged")

    context_columns = [
        "trading_day",
        "observations",
        "ordinary_spearman",
        "partial_controlling_momentum",
        "partial_controlling_raw",
        "partial_controlling_both",
        "hedge_raw_spearman",
        "hedge_momentum_spearman",
        "raw_momentum_spearman",
        "rank_hedge_r2_from_both_controls",
        "rank_target_r2_from_both_controls",
        "rank_hedge_residual_std",
        "rank_target_residual_std",
    ]
    print("\nCONTROL / RESIDUALIZATION CONTEXT")
    print(result[context_columns].to_string(index=False))

    loo_columns = [
        "trading_day",
        "ordinary_loo_count",
        "ordinary_loo_negative_count",
        "ordinary_loo_negative_pct",
        "ordinary_loo_median",
        "ordinary_loo_min",
        "ordinary_loo_max",
        "ordinary_loo_max_abs_change",
        "ordinary_loo_any_sign_flip",
        "controlled_loo_count",
        "controlled_loo_negative_count",
        "controlled_loo_negative_pct",
        "controlled_loo_median",
        "controlled_loo_min",
        "controlled_loo_max",
        "controlled_loo_max_abs_change",
        "controlled_loo_any_sign_flip",
    ]
    print("\nLEAVE-ONE-MINUTE-OUT STABILITY")
    print(result[loo_columns].to_string(index=False))

    concentration_columns = [
        "trading_day",
        "ordinary_largest_abs_contribution_share",
        "ordinary_top3_abs_contribution_share",
        "ordinary_top5_abs_contribution_share",
        "ordinary_largest_abs_contribution_timestamp",
        "ordinary_largest_abs_contribution_sign",
        "controlled_largest_abs_contribution_share",
        "controlled_top3_abs_contribution_share",
        "controlled_top5_abs_contribution_share",
        "controlled_largest_abs_contribution_timestamp",
        "controlled_largest_abs_contribution_sign",
    ]
    print("\nRANK-PRODUCT CONTRIBUTION CONCENTRATION")
    print(result[concentration_columns].to_string(index=False))

    print(f"\nOUTPUT CSV: {output}")
    print("NO PAID DATA REQUESTS: this audit reads only existing local Batch-4 feature CSVs.")
    print("NO OBSERVATION REMOVAL: leave-one-out values are influence diagnostics only; official Batch-4 endpoints remain unchanged.")
    print("INTERPRETATION LIMIT: residualization/influence diagnostics do not establish causality, dealer inventory, or production edge.")


if __name__ == "__main__":
    main()
