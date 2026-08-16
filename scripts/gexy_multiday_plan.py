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


def _metadata_cost(client, day: date) -> tuple[float, float, float]:
    definition_cost = _definition_cost(client, day)
    statistics_cost = _statistics_cost(client, day)
    return definition_cost, statistics_cost, definition_cost + statistics_cost


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
            "already exists. Use --build-missing-chains only with an explicit "
            "--max-metadata-download-cost; all missing-chain metadata is re-priced and checked "
            "against that fail-closed guard before any definition/OI download begins."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--build-missing-chains", action="store_true")
    parser.add_argument(
        "--max-metadata-download-cost",
        type=float,
        default=0.0,
        help=(
            "Maximum total estimated definition+OI download cost allowed for missing chains. "
            "Default 0.0 makes --build-missing-chains fail closed until a reviewed cap is explicit."
        ),
    )
    args = parser.parse_args()

    if args.max_metadata_download_cost < 0:
        raise SystemExit("--max-metadata-download-cost must be nonnegative")

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

    rows: list[dict[str, object]] = []
    row_by_day: dict[date, dict[str, object]] = {}
    missing_days: list[date] = []

    for day in args.dates:
        definition_cost, statistics_cost, metadata_cost = _metadata_cost(client, day)
        path = _chain_path(day)
        chain: pd.DataFrame | None = None
        chain_status = "cached" if path.exists() else "missing"

        if path.exists():
            chain = pd.read_csv(path)
        else:
            missing_days.append(day)

        cbbo_cost: float | None = None
        contracts: int | None = None
        if chain is not None and not chain.empty:
            contracts = int(chain["raw_symbol"].dropna().astype(str).nunique())
            cbbo_cost = _cbbo_cost(client, day, chain)

        row = {
            "date": day.isoformat(),
            "definition_cost": definition_cost,
            "statistics_cost": statistics_cost,
            "metadata_cost": metadata_cost,
            "chain_status": chain_status,
            "contracts": contracts,
            "cbbo_1m_cost": cbbo_cost,
        }
        rows.append(row)
        row_by_day[day] = row

    if args.build_missing_chains and missing_days:
        # Re-price every missing day's paid metadata immediately before the batch starts.
        # No definition/statistics download occurs until the whole re-priced batch fits the cap.
        repriced: dict[date, tuple[float, float, float]] = {
            day: _metadata_cost(client, day) for day in missing_days
        }
        repriced_total = sum(item[2] for item in repriced.values())

        print("\nMISSING-CHAIN DOWNLOAD PREFLIGHT")
        for day in missing_days:
            definition_cost, statistics_cost, metadata_cost = repriced[day]
            print(
                f"{day.isoformat()} definition=${definition_cost:.6f} "
                f"statistics=${statistics_cost:.6f} total=${metadata_cost:.6f}"
            )
        print(f"RE-PRICED MISSING-CHAIN METADATA TOTAL: ${repriced_total:.6f}")
        print(f"METADATA DOWNLOAD COST GUARD: ${args.max_metadata_download_cost:.6f}")

        if repriced_total > args.max_metadata_download_cost + 1e-12:
            raise SystemExit(
                "ABORTED BEFORE DOWNLOAD: re-priced missing-chain metadata cost exceeds "
                "--max-metadata-download-cost. Increase the guard explicitly only after "
                "reviewing the estimate."
            )

        print("PREFLIGHT PASSED: beginning definition/OI downloads within reviewed estimate guard.")

        for day in missing_days:
            definition_cost, statistics_cost, metadata_cost = repriced[day]
            row = row_by_day[day]
            row["definition_cost"] = definition_cost
            row["statistics_cost"] = statistics_cost
            row["metadata_cost"] = metadata_cost

            chain = _build_chain(client, db, day)
            path = _chain_path(day)
            if chain.empty:
                print(f"{day.isoformat()} no same-day SPXW contracts with OI; chain not saved")
                row["chain_status"] = "empty"
                continue

            chain.to_csv(path, index=False)
            row["chain_status"] = "built"
            row["contracts"] = int(chain["raw_symbol"].dropna().astype(str).nunique())
            row["cbbo_1m_cost"] = _cbbo_cost(client, day, chain)
            print(f"{day.isoformat()} saved chain: {path} ({len(chain)} contracts)")

    summary = pd.DataFrame(rows)
    total_metadata_cost = float(summary["metadata_cost"].sum())
    priced_cbbo = pd.to_numeric(summary["cbbo_1m_cost"], errors="coerce")
    cbbo_priced_days = int(priced_cbbo.notna().sum())
    total_cbbo_cost = float(priced_cbbo.fillna(0.0).sum())

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

    if args.build_missing_chains:
        print(
            "NOTE: --build-missing-chains downloaded definition/statistics data only after the "
            "re-priced total fit within --max-metadata-download-cost. The guard is a local "
            "preflight estimate guard, not a vendor transactional billing cap. Full-day CBBO "
            "quotes were not downloaded."
        )
    else:
        print(
            "NOTE: Default mode makes metadata cost-estimate calls only and downloads no market "
            "data. --build-missing-chains requires an explicit reviewed "
            "--max-metadata-download-cost before any definition/OI download can begin."
        )


if __name__ == "__main__":
    main()
