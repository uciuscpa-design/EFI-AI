from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_control_structure import DEFAULT_HORIZONS, score_control_structure


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_MIN_VOLUME_COVERAGE = 0.90


def _parse_dates(value: str) -> tuple[str, ...]:
    dates = tuple(item.strip() for item in value.split(",") if item.strip())
    if not dates:
        raise argparse.ArgumentTypeError("--dates must contain at least one YYYY-MM-DD date")
    for item in dates:
        try:
            pd.Timestamp(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates") from exc
    return dates


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        result = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--horizons must be comma-separated integers") from exc
    if not result or any(item < 1 for item in result):
        raise argparse.ArgumentTypeError("--horizons must contain positive minutes")
    return result


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit GEXY net-delta control structure on existing local causal feature files. "
            "Reports ordinary and partial rank associations without selecting a new signal or making a market-data request."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--horizons", type=_parse_horizons, default=DEFAULT_HORIZONS)
    parser.add_argument(
        "--min-volume-coverage",
        type=float,
        default=DEFAULT_MIN_VOLUME_COVERAGE,
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    if not 0.0 <= args.min_volume_coverage <= 1.0:
        parser.error("--min-volume-coverage must be between 0 and 1")

    frames: list[pd.DataFrame] = []
    for day in args.dates:
        raw_path = _raw_path(args.data_dir, day)
        hedge_path = _hedge_path(args.data_dir, day)
        if not raw_path.exists():
            raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
        if not hedge_path.exists():
            raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")
        raw = pd.read_csv(raw_path)
        hedge = pd.read_csv(hedge_path)
        frames.append(
            score_control_structure(
                raw,
                hedge,
                trading_day=day,
                horizons_minutes=args.horizons,
                min_volume_coverage=args.min_volume_coverage,
            )
        )

    result = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    if result.empty:
        raise SystemExit("no control-structure rows were available")

    output = args.data_dir / "gexy_spxw_tradeflow_control_structure_audit.csv"
    args.data_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)

    print("GEXY BATCH-3 CONTROL-STRUCTURE AUDIT — LOCAL ONLY")
    print(f"DATES: {','.join(args.dates)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("SIGNAL: hedge_delta_units")
    print("CONTROLS: backward_return_1m_bps and flow_net_signed_contracts")
    print("STATUS: post-validation statistical diagnostic; batch-3 verdict is unchanged")

    display = [
        "trading_day",
        "horizon_minutes",
        "observations",
        "hedge_target_spearman",
        "raw_target_spearman",
        "momentum_target_spearman",
        "hedge_raw_spearman",
        "hedge_momentum_spearman",
        "raw_momentum_spearman",
        "hedge_partial_controlling_momentum",
        "hedge_partial_controlling_raw",
        "hedge_partial_controlling_momentum_and_raw",
        "ordinary_to_both_sign_flip",
    ]
    print("\nCONTROL-STRUCTURE RESULTS")
    print(result[display].to_string(index=False))
    print(f"\nOUTPUT CSV: {output}")
    print("NO PAID DATA REQUESTS: this audit reads only existing local causal feature CSVs.")


if __name__ == "__main__":
    main()
