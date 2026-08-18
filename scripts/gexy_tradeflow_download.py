from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

import pandas as pd

from packages.core.config import get_settings

try:
    from scripts.gexy_tradeflow_plan import (
        DATASET,
        _chain_path,
        _chain_symbols,
        _estimate_schema_cost,
        _filter_chain_by_strike_band,
        _market_window,
        _opening_forward,
        _parse_windows,
        _window_label,
    )
except ModuleNotFoundError as exc:
    # When this file is launched directly as
    # `python scripts/gexy_tradeflow_download.py`, Python places the scripts
    # directory itself on sys.path rather than exposing `scripts` as an
    # importable package. Fall back to the sibling module in that execution
    # mode while preserving the package import used by pytest/module callers.
    if exc.name != "scripts":
        raise
    from gexy_tradeflow_plan import (
        DATASET,
        _chain_path,
        _chain_symbols,
        _estimate_schema_cost,
        _filter_chain_by_strike_band,
        _market_window,
        _opening_forward,
        _parse_windows,
        _window_label,
    )


SCHEMA = "tcbbo"
DEFAULT_WINDOWS = _parse_windows("09:30-10:00,15:30-16:00")
DEFAULT_STRIKE_BAND_POINTS = 200.0
DEFAULT_MAX_COST = 5.0
ABSOLUTE_MAX_COST = 5.0
DEFAULT_OUTPUT_DIR = Path("data/gexy/tradeflow")


@dataclass(frozen=True)
class WindowPlan:
    window: tuple[time, time]
    cost: float
    output_path: Path


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--date must use YYYY-MM-DD") from exc


def _load_selected_symbols(day: date, band_points: float) -> tuple[float, list[str]]:
    if band_points <= 0:
        raise ValueError("strike band must be positive")

    chain_path = _chain_path(day)
    if not chain_path.exists():
        raise ValueError(f"cached chain was not found: {chain_path}")

    chain = pd.read_csv(chain_path)
    opening_forward = _opening_forward(day)
    selected = _filter_chain_by_strike_band(
        chain,
        anchor=opening_forward,
        band_points=band_points,
    )
    if selected.empty:
        raise ValueError(
            f"{day.isoformat()} strike band selected no contracts around opening forward "
            f"{opening_forward:.3f}"
        )
    return opening_forward, _chain_symbols(selected)


def _window_output_path(output_dir: Path, day: date, window: tuple[time, time]) -> Path:
    start, end = window
    return output_dir / (
        f"gexy_spxw_{day.isoformat()}_{start.strftime('%H%M')}_{end.strftime('%H%M')}_tcbbo.dbn.zst"
    )


def _build_plan(
    client,
    *,
    day: date,
    symbols: list[str],
    windows: tuple[tuple[time, time], ...],
    output_dir: Path,
) -> tuple[WindowPlan, ...]:
    plans: list[WindowPlan] = []
    for window in windows:
        plans.append(
            WindowPlan(
                window=window,
                cost=_estimate_schema_cost(client, day, symbols, SCHEMA, window=window),
                output_path=_window_output_path(output_dir, day, window),
            )
        )
    return tuple(plans)


def _total_cost(plans: tuple[WindowPlan, ...]) -> float:
    return float(sum(item.cost for item in plans))


def _validate_cost_cap(*, total_cost: float, max_cost: float) -> None:
    if max_cost <= 0:
        raise ValueError("--max-cost must be positive")
    if max_cost > ABSOLUTE_MAX_COST:
        raise ValueError(
            f"--max-cost may not exceed the hard safety ceiling of ${ABSOLUTE_MAX_COST:.2f}"
        )
    if total_cost > max_cost:
        raise ValueError(
            f"estimated TCBBO cost ${total_cost:.6f} exceeds --max-cost ${max_cost:.2f}; refusing download"
        )


def _assert_outputs_absent(plans: tuple[WindowPlan, ...]) -> None:
    collisions = [str(item.output_path) for item in plans if item.output_path.exists()]
    partials = [
        str(item.output_path.with_suffix(item.output_path.suffix + ".partial"))
        for item in plans
        if item.output_path.with_suffix(item.output_path.suffix + ".partial").exists()
    ]
    blocked = collisions + partials
    if blocked:
        raise ValueError(
            "refusing to overwrite existing trade-flow files: " + ", ".join(blocked)
        )


def _download_window(client, *, day: date, symbols: list[str], plan: WindowPlan) -> None:
    start, end = _market_window(day, plan.window)
    final_path = plan.output_path
    partial_path = final_path.with_suffix(final_path.suffix + ".partial")
    final_path.parent.mkdir(parents=True, exist_ok=True)

    client.timeseries.get_range(
        dataset=DATASET,
        schema=SCHEMA,
        stype_in="raw_symbol",
        symbols=symbols,
        start=start.isoformat(),
        end=end.isoformat(),
        path=str(partial_path),
    )
    os.replace(partial_path, final_path)


def _print_plan(
    *,
    day: date,
    opening_forward: float,
    symbols: list[str],
    band_points: float,
    plans: tuple[WindowPlan, ...],
    max_cost: float,
) -> None:
    rows = [
        {
            "date": day.isoformat(),
            "window": _window_label(item.window),
            "contracts": len(symbols),
            "tcbbo_cost": item.cost,
            "output": str(item.output_path),
        }
        for item in plans
    ]
    print("GEXY TCBBO DOWNLOAD PLAN")
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\nOPENING FORWARD: {opening_forward:.6f}")
    print(f"STRIKE SCOPE: opening-forward +/- {band_points:g} SPX points")
    print(f"EXACT SYMBOLS: {len(symbols)}")
    print(f"ESTIMATED TOTAL TCBBO COST: ${_total_cost(plans):.6f}")
    print(f"REQUESTED MAX COST: ${max_cost:.2f}")
    print(f"HARD SAFETY CEILING: ${ABSOLUTE_MAX_COST:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed downloader for bounded GEXY SPXW TCBBO research data. "
            "Without --execute it prices the exact request and downloads nothing."
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
        "--strike-band-points",
        type=float,
        default=DEFAULT_STRIKE_BAND_POINTS,
        help="symmetric strike band around the cached opening forward; default: 200",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=DEFAULT_MAX_COST,
        help="maximum estimated total cost allowed; hard ceiling is $5.00",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="directory for raw DBN files",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually download after a second cost check; omit for a no-download dry run",
    )
    args = parser.parse_args()

    if args.strike_band_points <= 0:
        parser.error("--strike-band-points must be positive")
    if args.max_cost <= 0:
        parser.error("--max-cost must be positive")
    if args.max_cost > ABSOLUTE_MAX_COST:
        parser.error(
            f"--max-cost may not exceed the hard safety ceiling of ${ABSOLUTE_MAX_COST:.2f}"
        )

    try:
        opening_forward, symbols = _load_selected_symbols(
            args.trading_day,
            float(args.strike_band_points),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    settings = get_settings()
    if not settings.databento_api_key:
        raise SystemExit("DATABENTO_API_KEY was not found in .env")

    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit(
            "databento is not installed. Run with: uv run --with databento --with pandas python ..."
        ) from exc

    client = db.Historical(settings.databento_api_key)
    plans = _build_plan(
        client,
        day=args.trading_day,
        symbols=symbols,
        windows=args.windows,
        output_dir=args.output_dir,
    )

    _print_plan(
        day=args.trading_day,
        opening_forward=opening_forward,
        symbols=symbols,
        band_points=float(args.strike_band_points),
        plans=plans,
        max_cost=float(args.max_cost),
    )

    try:
        _validate_cost_cap(total_cost=_total_cost(plans), max_cost=float(args.max_cost))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if not args.execute:
        print("DRY RUN ONLY: no market data downloaded. Re-run with --execute only after reviewing this plan.")
        return

    try:
        _assert_outputs_absent(plans)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    # Re-price the exact request immediately before any paid download.
    execution_plans = _build_plan(
        client,
        day=args.trading_day,
        symbols=symbols,
        windows=args.windows,
        output_dir=args.output_dir,
    )
    execution_total = _total_cost(execution_plans)
    try:
        _validate_cost_cap(total_cost=execution_total, max_cost=float(args.max_cost))
    except ValueError as exc:
        raise SystemExit(f"PRE-DOWNLOAD COST RECHECK FAILED: {exc}") from exc

    print(f"PRE-DOWNLOAD COST RECHECK: ${execution_total:.6f} — within cap")
    for item in execution_plans:
        print(
            f"DOWNLOADING {_window_label(item.window)} -> {item.output_path} "
            f"(estimated ${item.cost:.6f})"
        )
        _download_window(
            client,
            day=args.trading_day,
            symbols=symbols,
            plan=item,
        )
        print(f"CACHED RAW TCBBO: {item.output_path}")

    print(
        f"GEXY TCBBO PILOT COMPLETE: {len(execution_plans)} window(s), "
        f"pre-download estimated total ${execution_total:.6f}"
    )


if __name__ == "__main__":
    main()
