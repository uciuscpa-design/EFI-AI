from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from packages.core.config import get_settings


NY = ZoneInfo("America/New_York")
DATASET = "OPRA.PILLAR"
ROOT = "SPXW"
PARENT = f"{ROOT}.OPT"


def _parse_dates(value: str) -> tuple[date, ...]:
    items: list[date] = []
    for raw in value.split(","):
        raw = raw.strip()
        if raw:
            items.append(date.fromisoformat(raw))
    unique = tuple(sorted(set(items)))
    if not unique:
        raise argparse.ArgumentTypeError("--dates must contain at least one ISO date")
    return unique


def _chain_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_0dte_oi.csv")


def _definition_cost(client, day: date) -> float:
    return float(
        client.metadata.get_cost(
            dataset=DATASET,
            schema="definition",
            stype_in="parent",
            symbols=[PARENT],
            start=day.isoformat(),
            end=(day + timedelta(days=1)).isoformat(),
        )
    )


def _statistics_cost(client, day: date) -> float:
    cutoff = datetime.combine(day, time(9, 30), tzinfo=NY)
    return float(
        client.metadata.get_cost(
            dataset=DATASET,
            schema="statistics",
            stype_in="parent",
            symbols=[PARENT],
            start=day.isoformat(),
            end=cutoff.isoformat(),
        )
    )


def _cbbo_cost(client, day: date, chain: pd.DataFrame) -> float:
    symbols = chain["raw_symbol"].dropna().astype(str).unique().tolist()
    if not symbols:
        raise ValueError("chain has no raw_symbol values")
    start = datetime.combine(day, time(9, 30), tzinfo=NY)
    end = datetime.combine(day, time(16, 0), tzinfo=NY)
    return float(
        client.metadata.get_cost(
            dataset=DATASET,
            schema="cbbo-1m",
            stype_in="raw_symbol",
            symbols=symbols,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    )


def _build_chain(client, db, day: date) -> pd.DataFrame:
    next_day = day + timedelta(days=1)
    definitions = client.timeseries.get_range(
        dataset=DATASET,
        schema="definition",
        stype_in="parent",
        symbols=[PARENT],
        start=day.isoformat(),
        end=next_day.isoformat(),
    ).to_df().reset_index()
    definitions = definitions.sort_values("ts_recv").drop_duplicates("instrument_id", keep="last")
    definitions["expiration"] = pd.to_datetime(
        definitions["expiration"], utc=True, errors="coerce"
    )
    definitions = definitions.loc[definitions["expiration"].dt.date == day].copy()

    oi_cutoff = datetime.combine(day, time(9, 30), tzinfo=NY)
    stats = client.timeseries.get_range(
        dataset=DATASET,
        schema="statistics",
        stype_in="parent",
        symbols=[PARENT],
        start=day.isoformat(),
        end=oi_cutoff.isoformat(),
    ).to_df().reset_index()
    stats = stats[stats["stat_type"] == db.StatType.OPEN_INTEREST].sort_values("ts_recv")
    stats = stats.drop_duplicates("instrument_id", keep="last")
    oi = stats[["instrument_id", "quantity"]].rename(columns={"quantity": "open_interest"})

    chain = definitions.merge(oi, on="instrument_id", how="left")
    required = ["raw_symbol", "instrument_class", "strike_price", "open_interest"]
    chain = chain.dropna(subset=required).copy()
    chain["instrument_class"] = chain["instrument_class"].astype(str).str.upper()
    chain = chain[chain["instrument_class"].isin(["C", "P"])]
    return chain.drop_duplicates("raw_symbol", keep="last")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Plan a multi-session SPXW 0DTE Databento expansion. By default this only prices "
            "definition/statistics requests and prices exact-symbol CBBO when a local chain CSV "
            "already exists. Use --build-missing-chains to download only the small daily "
            "definition/OI inputs, save chains, and then price exact-symbol CBBO for every day."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--build-missing-chains", action="store_true")
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

    total_metadata_cost = 0.0
    total_cbbo_cost = 0.0
    cbbo_priced_days = 0
    rows: list[dict[str, object]] = []

    for day in args.dates:
        definition_cost = _definition_cost(client, day)
        statistics_cost = _statistics_cost(client, day)
        metadata_cost = definition_cost + statistics_cost
        total_metadata_cost += metadata_cost

        path = _chain_path(day)
        chain: pd.DataFrame | None = None
        chain_status = "cached" if path.exists() else "missing"

        if path.exists():
            chain = pd.read_csv(path)
        elif args.build_missing_chains:
            print(
                f"{day.isoformat()} metadata estimated cost before chain build: "
                f"${metadata_cost:.6f}"
            )
            chain = _build_chain(client, db, day)
            if chain.empty:
                print(f"{day.isoformat()} no same-day SPXW contracts with OI; chain not saved")
                chain_status = "empty"
            else:
                chain.to_csv(path, index=False)
                chain_status = "built"
                print(f"{day.isoformat()} saved chain: {path} ({len(chain)} contracts)")

        cbbo_cost: float | None = None
        contracts: int | None = None
        if chain is not None and not chain.empty:
            contracts = int(chain["raw_symbol"].dropna().astype(str).nunique())
            cbbo_cost = _cbbo_cost(client, day, chain)
            total_cbbo_cost += cbbo_cost
            cbbo_priced_days += 1

        rows.append(
            {
                "date": day.isoformat(),
                "definition_cost": definition_cost,
                "statistics_cost": statistics_cost,
                "metadata_cost": metadata_cost,
                "chain_status": chain_status,
                "contracts": contracts,
                "cbbo_1m_cost": cbbo_cost,
            }
        )

    summary = pd.DataFrame(rows)
    print("\nMULTI-DAY COST PLAN")
    print(summary.to_string(index=False, na_rep="pending"))
    print(f"\nDATES: {len(args.dates)}")
    print(f"ESTIMATED DEFINITION+OI COST IF DOWNLOADED FOR ALL DATES: ${total_metadata_cost:.6f}")
    if cbbo_priced_days:
        print(
            f"EXACT-SYMBOL FULL-DAY CBBO COST FOR {cbbo_priced_days} PRICED DATE(S): "
            f"${total_cbbo_cost:.6f}"
        )
    if cbbo_priced_days < len(args.dates):
        print(
            "CBBO TOTAL IS PARTIAL: missing chain CSVs must be built before exact-symbol quote "
            "costs can be estimated for those dates."
        )
    else:
        print(
            "ESTIMATED TOTAL (DEFINITION+OI + ALL PRICED CBBO): "
            f"${total_metadata_cost + total_cbbo_cost:.6f}"
        )

    print(
        "NOTE: Default mode makes metadata cost-estimate calls only. --build-missing-chains "
        "downloads definition/statistics data for missing dates and therefore incurs those "
        "small metadata charges; it still does not download full-day CBBO quotes."
    )


if __name__ == "__main__":
    main()
