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


def _parse_dates(value: str) -> tuple[date, ...]:
    days = tuple(sorted({date.fromisoformat(item.strip()) for item in value.split(",") if item.strip()}))
    if not days:
        raise argparse.ArgumentTypeError("--dates must contain at least one ISO date")
    return days


def _chain_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_0dte_oi.csv")


def _market_window(day: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, time(9, 30), tzinfo=NY),
        datetime.combine(day, time(16, 0), tzinfo=NY),
    )


def _chain_symbols(chain: pd.DataFrame) -> list[str]:
    if "raw_symbol" not in chain.columns:
        raise ValueError("chain CSV is missing raw_symbol")
    symbols = sorted(chain["raw_symbol"].dropna().astype(str).str.strip().loc[lambda item: item != ""].unique())
    if not symbols:
        raise ValueError("chain has no raw_symbol values")
    return symbols


def _estimate_schema_cost(client, day: date, symbols: list[str], schema: str) -> float:
    if schema not in SUPPORTED_SCHEMAS:
        raise ValueError(f"unsupported schema: {schema}")
    start, end = _market_window(day)
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
    args = parser.parse_args()

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

    rows: list[dict[str, object]] = []
    totals = {schema: 0.0 for schema in schemas}
    priced_days = 0

    for day in args.dates:
        path = _chain_path(day)
        if not path.exists():
            rows.append(
                {
                    "date": day.isoformat(),
                    "chain_status": "missing",
                    "contracts": None,
                    **{f"{schema}_cost": None for schema in schemas},
                }
            )
            continue

        chain = pd.read_csv(path)
        symbols = _chain_symbols(chain)
        row: dict[str, object] = {
            "date": day.isoformat(),
            "chain_status": "cached",
            "contracts": len(symbols),
        }
        for schema in schemas:
            cost = _estimate_schema_cost(client, day, symbols, schema)
            row[f"{schema}_cost"] = cost
            totals[schema] += cost
        rows.append(row)
        priced_days += 1

    summary = pd.DataFrame(rows)
    print("GEXY TRADE-FLOW COST PLAN — NO MARKET-DATA DOWNLOAD")
    print(summary.to_string(index=False, na_rep="pending"))
    print(f"\nDATES REQUESTED: {len(args.dates)}")
    print(f"DATES PRICED FROM CACHED CHAINS: {priced_days}")
    for schema in schemas:
        print(f"ESTIMATED EXACT-SYMBOL FULL-DAY {schema.upper()} COST: ${totals[schema]:.6f}")

    missing = len(args.dates) - priced_days
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
        "SAFETY: this script calls Historical.metadata.get_cost only. It does not call timeseries.get_range, "
        "batch.submit_job, or download any TCBBO/trades records. Running it estimates cost only."
    )


if __name__ == "__main__":
    main()
