from __future__ import annotations

import argparse
from datetime import date, time
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_features import FLOW_FEATURES, aggregate_completed_minute_flow, join_flow_to_replay

try:
    from scripts.gexy_tradeflow_plan import _parse_windows, _window_label
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from gexy_tradeflow_plan import _parse_windows, _window_label


DEFAULT_WINDOWS = _parse_windows("09:30-10:00,15:30-16:00")
DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_HORIZONS = (1, 5, 15, 30, 60)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--date must use YYYY-MM-DD") from exc


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        result = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--horizons must be comma-separated integers") from exc
    if not result or any(item < 1 for item in result):
        raise argparse.ArgumentTypeError("--horizons must contain positive minutes")
    return result


def _classified_path(data_dir: Path, day: date, window: tuple[time, time]) -> Path:
    start, end = window
    return data_dir / (
        f"gexy_spxw_{day.isoformat()}_{start.strftime('%H%M')}_{end.strftime('%H%M')}_tcbbo_classified.csv"
    )


def _replay_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_replay_features.csv")


def _output_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_tradeflow_minute_features.csv"


def _read_classified_windows(
    data_dir: Path,
    day: date,
    windows: tuple[tuple[time, time], ...],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for window in windows:
        path = _classified_path(data_dir, day, window)
        if not path.exists():
            raise ValueError(f"classified TCBBO CSV was not found: {path}")
        frame = pd.read_csv(path)
        frame["source_window"] = _window_label(window)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build strictly causal completed-minute GEXY trade-flow features from local classified TCBBO CSVs "
            "and join them to the cached replay state/forward-return labels. Makes no market-data requests."
        )
    )
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument(
        "--windows",
        type=_parse_windows,
        default=DEFAULT_WINDOWS,
        help="comma-separated New York windows; default: 09:30-10:00,15:30-16:00",
    )
    parser.add_argument(
        "--horizons",
        type=_parse_horizons,
        default=DEFAULT_HORIZONS,
        help="forward-return label horizons in minutes; default: 1,5,15,30,60",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing local classified TCBBO CSVs",
    )
    args = parser.parse_args()

    try:
        classified = _read_classified_windows(args.data_dir, args.trading_day, args.windows)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    replay_path = _replay_path(args.trading_day)
    if not replay_path.exists():
        raise SystemExit(f"cached replay feature CSV was not found: {replay_path}")

    try:
        minute_flow = aggregate_completed_minute_flow(classified)
        combined = join_flow_to_replay(
            minute_flow,
            pd.read_csv(replay_path),
            horizons_minutes=args.horizons,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = _output_path(args.data_dir, args.trading_day)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)

    matched = int(combined["replay_match"].sum())
    total = len(combined)
    print("GEXY CAUSAL MINUTE TRADE-FLOW FEATURES")
    print(f"DATE: {args.trading_day.isoformat()}")
    print(f"INPUT WINDOWS: {','.join(_window_label(item) for item in args.windows)}")
    print(f"COMPLETED FLOW MINUTES: {total}")
    print(f"REPLAY-MATCHED MINUTES: {matched}/{total}")
    if total:
        print(f"REPLAY MATCH PCT: {matched / total:.1%}")
    print("CAUSAL ALIGNMENT: flow during minute M is timestamped M+1 before joining to replay/labels")
    print(f"FLOW FEATURES: {len(FLOW_FEATURES)}")
    print(f"OUTPUT CSV: {output}")

    display_columns = [
        "flow_minute",
        "timestamp",
        "flow_trade_records",
        "flow_classification_rate",
        "flow_net_signed_contracts",
        "flow_contract_imbalance",
        "flow_net_signed_premium_notional",
        "flow_premium_imbalance",
        "forward",
    ]
    for horizon in args.horizons:
        column = f"forward_return_{horizon}m_bps"
        if column in combined.columns:
            display_columns.append(column)
    print("\nLAST 8 CAUSAL MINUTE ROWS")
    print(combined[display_columns].tail(8).to_string(index=False))
    print("\nNO PAID DATA REQUESTS: this feature builder reads only local classified CSVs and cached replay data.")


if __name__ == "__main__":
    main()
