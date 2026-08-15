from __future__ import annotations

import argparse
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from packages.core.config import get_settings


NY = ZoneInfo("America/New_York")
DATASET = "OPRA.PILLAR"
ROOT = "SPXW"
DEFAULT_SCHEMA = "tcbbo"
SUPPORTED_SCHEMAS = ("tcbbo", "trades")
SESSION_OPEN = time(9, 30)
SESSION_CLOSE = time(16, 0)


def _parse_dates(value: str) -> tuple[date, ...]:
    days = tuple(sorted({date.fromisoformat(item.strip()) for item in value.split(",") if item.strip()}))
    if not days:
        raise argparse.ArgumentTypeError("--dates must contain at least one ISO date")
    return days


def _parse_clock(value: str) -> time:
    try:
        parsed = datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("times must use HH:MM in New York local time") from exc
    if parsed < SESSION_OPEN or parsed > SESSION_CLOSE:
        raise argparse.ArgumentTypeError("window times must stay within 09:30-16:00 New York time")
    return parsed


def _parse_windows(value: str) -> tuple[tuple[time, time], ...]:
    windows: list[tuple[time, time]] = []
    for item in value.split(","):
        raw = item.strip()
        if not raw:
            continue
        try:
            start_text, end_text = raw.split("-", 1)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("windows must look like 09:30-10:00,15:30-16:00") from exc
        start = _parse_clock(start_text)
        end = _parse_clock(end_text)
        if end <= start:
            raise argparse.ArgumentTypeError("each window end must be after its start")
        windows.append((start, end))

    if not windows:
        raise argparse.ArgumentTypeError("--windows must contain at least one time range")

    ordered = tuple(sorted(set(windows), key=lambda item: item[0]))
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] < previous[1]:
            raise argparse.ArgumentTypeError("cost-plan windows must not overlap")
    return ordered


def _chain_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_0dte_oi.csv")


def _features_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_replay_features.csv")


def _market_window(day: date, window: tuple[time, time] | None = None) -> tuple[datetime, datetime]:
    selected = window or (SESSION_OPEN, SESSION_CLOSE)
    return (
        datetime.combine(day, selected[0], tzinfo=NY),
        datetime.combine(day, selected[1], tzinfo=NY),
    )


def _window_label(window: tuple[time, time]) -> str:
    return f"{window[0].strftime('%H:%M')}-{window[1].strftime('%H:%M')}"


def _chain_symbols(chain: pd.DataFrame) -> list[str]:
    if "raw_symbol" not in chain.columns:
        raise ValueError("chain CSV is missing raw_symbol")
    symbols = sorted(chain["raw_symbol"].dropna().astype(str).str.strip().loc[lambda item: item != ""].unique())
    if not symbols:
        raise ValueError("chain has no raw_symbol values")
    return symbols


def _opening_forward(day: date) -> float:
    path = _features_path(day)
    if not path.exists():
        raise ValueError(f"opening-forward anchor requires cached replay features: {path}")
    frame = pd.read_csv(path, usecols=["timestamp", "forward"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame["forward"] = pd.to_numeric(frame["forward"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "forward"]).sort_values("timestamp")
    if frame.empty:
        raise ValueError(f"cached replay features contain no finite forward values: {path}")
    return float(frame.iloc[0]["forward"])


def _filter_chain_by_strike_band(chain: pd.DataFrame, *, anchor: float, band_points: float) -> pd.DataFrame:
    if band_points <= 0:
        raise ValueError("strike band must be positive")
    if "strike_price" not in chain.columns:
        raise ValueError("chain CSV is missing strike_price")
    strikes = pd.to_numeric(chain["strike_price"], errors="coerce")
    return chain.loc[strikes.sub(float(anchor)).abs() <= float(band_points)].copy()


def _estimate_schema_cost(
    client,
    day: date,
    symbols: list[str],
    schema: str,
    *,
    window: tuple[time, time] | None = None,
) -> float:
    if schema not in SUPPORTED_SCHEMAS:
        raise ValueError(f"unsupported schema: {schema}")
    start, end = _market_window(day, window)
    return float(
        client.metadata.get_cost(
            dataset=DATASET,
            schema=schema,
            stype_in="raw_symbol",
            symbols=symbols,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate exact-symbol SPXW 0DTE trade-flow data cost without downloading market data. "
            "TCBBO is the preferred GEXY upstream input because each trade is paired with the "
            "consolidated BBO immediately before the trade, which supports quote-based aggressor inference."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--schema",
        choices=("tcbbo", "trades", "both"),
        default=DEFAULT_SCHEMA,
        help="price TCBBO (preferred), raw trades, or both for comparison",
    )
    parser.add_argument(
        "--windows",
        type=_parse_windows,
        default=None,
        help=(
            "optional comma-separated New York windows such as "
            "09:30-10:00,12:30-13:00,15:30-16:00; default is the full 09:30-16:00 session"
        ),
    )
    parser.add_argument(
        "--strike-band-points",
        type=float,
        default=None,
        help=(
            "optional symmetric strike band around the first cached replay forward for each day; "
            "for example 200 keeps strikes within opening-forward +/- 200 SPX points"
        ),
    )
    args = parser.parse_args()

    if args.strike_band_points is not None and args.strike_band_points <= 0:
        parser.error("--strike-band-points must be positive")

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
    schemas = SUPPORTED_SCHEMAS if args.schema == "both" else (args.schema,)
    windows = args.windows or ((SESSION_OPEN, SESSION_CLOSE),)

    rows: list[dict[str, object]] = []
    totals = {schema: 0.0 for schema in schemas}
    priced_days: set[str] = set()

    for day in args.dates:
        path = _chain_path(day)
        if not path.exists():
            for window in windows:
                rows.append(
                    {
                        "date": day.isoformat(),
                        "window": _window_label(window),
                        "chain_status": "missing",
                        "opening_forward": None,
                        "contracts": None,
                        **{f"{schema}_cost": None for schema in schemas},
                    }
                )
            continue

        chain = pd.read_csv(path)
        opening_forward: float | None = None
        if args.strike_band_points is not None:
            try:
                opening_forward = _opening_forward(day)
                chain = _filter_chain_by_strike_band(
                    chain,
                    anchor=opening_forward,
                    band_points=float(args.strike_band_points),
                )
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
            if chain.empty:
                raise SystemExit(
                    f"{day.isoformat()} strike band selected no contracts around opening forward {opening_forward:.3f}"
                )

        symbols = _chain_symbols(chain)
        priced_days.add(day.isoformat())
        for window in windows:
            row: dict[str, object] = {
                "date": day.isoformat(),
                "window": _window_label(window),
                "chain_status": "cached",
                "opening_forward": opening_forward,
                "contracts": len(symbols),
            }
            for schema in schemas:
                cost = _estimate_schema_cost(client, day, symbols, schema, window=window)
                row[f"{schema}_cost"] = cost
                totals[schema] += cost
            rows.append(row)

    summary = pd.DataFrame(rows)
    print("GEXY TRADE-FLOW COST PLAN — NO MARKET-DATA DOWNLOAD")
    print(summary.to_string(index=False, na_rep="pending"))
    print(f"\nDATES REQUESTED: {len(args.dates)}")
    print(f"DATES PRICED FROM CACHED CHAINS: {len(priced_days)}")
    print(f"WINDOWS PER PRICED DAY: {','.join(_window_label(item) for item in windows)}")
    if args.strike_band_points is None:
        print("STRIKE SCOPE: all cached exact-symbol 0DTE contracts")
    else:
        print(
            "STRIKE SCOPE: opening-forward +/- "
            f"{float(args.strike_band_points):g} SPX points (fixed from cached first forward per day)"
        )
    for schema in schemas:
        print(f"ESTIMATED BOUNDED {schema.upper()} COST: ${totals[schema]:.6f}")

    missing = len(args.dates) - len(priced_days)
    if missing:
        print(f"MISSING CACHED CHAIN DAYS: {missing}; no estimate was attempted for those dates")

    if "tcbbo" in schemas:
        print(
            "TCBBO RESEARCH PURPOSE: each option trade is paired with the consolidated BBO immediately "
            "before the trade. OPRA does not disseminate trade aggressor side, so GEXY will infer "
            "buyer/seller initiation from trade price versus the pre-trade NBBO rather than treating "
            "the Databento side field as observed aggressor direction."
        )

    print(
        "SELECTION DISCIPLINE: optional strike filtering is anchored to the first cached replay forward "
        "for each day and is fixed before TCBBO inspection. Intraday windows are explicitly supplied on "
        "the command line."
    )
    print(
        "SAFETY: this script calls Historical.metadata.get_cost only. It does not call timeseries.get_range, "
        "batch.submit_job, or download any TCBBO/trades records. Running it estimates cost only."
    )


if __name__ == "__main__":
    main()
