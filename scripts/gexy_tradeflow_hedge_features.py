from __future__ import annotations

import argparse
from datetime import date, time
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_hedge import (
    HEDGE_FLOW_FEATURES,
    aggregate_hedge_flow_minutes,
    apply_dealer_hedge_proxy,
    build_symbol_minute_greeks,
    join_hedge_flow_to_replay,
)

try:
    from scripts.gexy_tradeflow_plan import _parse_windows, _window_label
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from gexy_tradeflow_plan import _parse_windows, _window_label


DEFAULT_WINDOWS = _parse_windows("09:30-10:00,15:30-16:00")
DEFAULT_HORIZONS = (1, 5, 15, 30, 60)
DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")


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
    return data_dir / f"gexy_spxw_{day.isoformat()}_tradeflow_hedge_features.csv"


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
            "Build causal Black-76 delta/gamma weighted GEXY trade-flow hedge proxies from local classified "
            "TCBBO files and cached replay state. Makes no market-data request."
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
        help="forward-return horizons in minutes; default: 1,5,15,30,60",
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
    replay = pd.read_csv(replay_path)

    try:
        symbol_greeks = build_symbol_minute_greeks(classified, replay)
        weighted = apply_dealer_hedge_proxy(classified, symbol_greeks)
        minute = aggregate_hedge_flow_minutes(weighted)
        combined = join_hedge_flow_to_replay(
            minute,
            replay,
            horizons_minutes=args.horizons,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = _output_path(args.data_dir, args.trading_day)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)

    solved = int(symbol_greeks["greek_solved"].sum())
    symbol_minutes = len(symbol_greeks)
    matched = int(combined["replay_match"].sum())

    print("GEXY GREEK-WEIGHTED TRADE-FLOW HEDGE PROXIES")
    print(f"DATE: {args.trading_day.isoformat()}")
    print(f"INPUT WINDOWS: {','.join(_window_label(item) for item in args.windows)}")
    print(f"SYMBOL-MINUTE GREEK SNAPSHOTS: {symbol_minutes}")
    print(f"GREEKS SOLVED: {solved}/{symbol_minutes} ({solved / symbol_minutes:.1%})" if symbol_minutes else "GREEKS SOLVED: 0/0")
    print(f"COMPLETED HEDGE-FLOW MINUTES: {len(combined)}")
    print(f"REPLAY-MATCHED AVAILABILITY MINUTES: {matched}/{len(combined)}")
    print(f"HEDGE FEATURES: {len(HEDGE_FLOW_FEATURES)}")
    print("CAUSALITY: minute-M quotes/flow/state are combined only into features timestamped M+1")
    print("SIGN: positive hedge_delta_units = opposite-side liquidity-provider proxy buys index-equivalent hedge")
    print("SIGN: positive hedge_gamma_units_per_point = customer option buying / opposite-side short-gamma acceleration")
    print("INTERPRETATION: proxy only; OPRA does not identify dealer inventory or executed hedge trades")
    print(f"OUTPUT CSV: {output}")

    display = [
        "flow_minute",
        "timestamp",
        "hedge_greek_solved_pct",
        "hedge_delta_units",
        "hedge_delta_notional",
        "hedge_gamma_units_per_point",
        "hedge_gax_notional_per_point",
        "hedge_gex_notional_per_1pct",
        "forward",
    ]
    for horizon in args.horizons:
        column = f"forward_return_{horizon}m_bps"
        if column in combined.columns:
            display.append(column)
    print("\nLAST 8 HEDGE-FLOW ROWS")
    print(combined[display].tail(8).to_string(index=False))
    print("\nNO PAID DATA REQUESTS: this script reads only local classified TCBBO CSVs and cached replay data.")


if __name__ == "__main__":
    main()
