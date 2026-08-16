from __future__ import annotations

import argparse
import subprocess
import sys
import time as time_module
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from packages.core.config import get_settings


NY = ZoneInfo("America/New_York")
DATASET = "OPRA.PILLAR"
HEARTBEAT_SECONDS = 30.0


def _parse_dates(value: str) -> tuple[date, ...]:
    days: list[date] = []
    seen: set[date] = set()
    for item in value.split(","):
        raw = item.strip()
        if not raw:
            continue
        day = date.fromisoformat(raw)
        if day not in seen:
            seen.add(day)
            days.append(day)
    if not days:
        raise argparse.ArgumentTypeError("--dates must contain at least one ISO date")
    return tuple(days)


def _chain_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_0dte_oi.csv")


def _quotes_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_0930_1600_cbbo_1m.csv")


def _features_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_replay_features.csv")


def _quote_cost(client, day: date, chain: pd.DataFrame) -> float:
    symbols = chain["raw_symbol"].dropna().astype(str).unique().tolist()
    if not symbols:
        raise ValueError(f"{day.isoformat()} chain has no raw_symbol values")
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


def _run_with_heartbeat(command: list[str], day: date) -> None:
    """Run one replay child while periodically showing that computation is alive."""
    started = time_module.monotonic()
    process = subprocess.Popen(command)
    try:
        while True:
            try:
                return_code = process.wait(timeout=HEARTBEAT_SECONDS)
                break
            except subprocess.TimeoutExpired:
                elapsed = time_module.monotonic() - started
                print(
                    f"{day.isoformat()} REPLAY STILL PROCESSING: "
                    f"elapsed={elapsed / 60.0:.1f}m pid={process.pid}",
                    flush=True,
                )
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        raise
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run multiple cached-or-download SPXW 0DTE replays with a fail-closed Databento "
            "cost guard. Without --download, only exact-symbol CBBO costs are estimated. With "
            "--download, missing quote days are re-priced immediately before the batch and are "
            "downloaded only when the re-priced total fits an explicit --max-new-cbbo-cost."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--horizons", default="1,5,15,30,60")
    parser.add_argument("--download", action="store_true")
    parser.add_argument(
        "--max-new-cbbo-cost",
        type=float,
        default=0.0,
        help=(
            "Maximum total estimated new CBBO-1m download cost. Default 0.0 makes --download "
            "fail closed until a reviewed cap is supplied explicitly."
        ),
    )
    args = parser.parse_args()

    if args.max_new_cbbo_cost < 0:
        raise SystemExit("--max-new-cbbo-cost must be nonnegative")

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
    plan_rows: list[dict[str, object]] = []
    chain_by_day: dict[date, pd.DataFrame] = {}
    total_new_cost = 0.0

    for day in args.dates:
        chain_path = _chain_path(day)
        if not chain_path.exists():
            raise SystemExit(f"missing chain CSV: {chain_path}")
        chain = pd.read_csv(chain_path)
        if "raw_symbol" not in chain.columns:
            raise SystemExit(f"chain CSV missing raw_symbol: {chain_path}")
        chain_by_day[day] = chain

        quote_path = _quotes_path(day)
        cached = quote_path.exists()
        cost = 0.0 if cached else _quote_cost(client, day, chain)
        total_new_cost += cost
        plan_rows.append(
            {
                "date": day.isoformat(),
                "contracts": int(chain["raw_symbol"].dropna().astype(str).nunique()),
                "quotes_cached": cached,
                "estimated_new_cbbo_cost": cost,
                "features_path": str(_features_path(day)),
            }
        )

    plan = pd.DataFrame(plan_rows)
    print("MULTI-DAY REPLAY PREFLIGHT")
    print(plan.to_string(index=False))
    print(f"\nESTIMATED NEW CBBO COST: ${total_new_cost:.6f}")
    print(f"COST GUARD: ${args.max_new_cbbo_cost:.6f}")

    if not args.download:
        print("NO MARKET DATA DOWNLOADED. Re-run with --download only after reviewing an explicit cost guard.")
        return

    missing_days = [day for day in args.dates if not _quotes_path(day).exists()]
    repriced_costs: dict[date, float] = {
        day: _quote_cost(client, day, chain_by_day[day]) for day in missing_days
    }
    repriced_total = sum(repriced_costs.values())

    print("\nCBBO DOWNLOAD PREFLIGHT REPRICE")
    for day in missing_days:
        print(f"{day.isoformat()} cbbo_1m=${repriced_costs[day]:.6f}")
    print(f"RE-PRICED NEW CBBO TOTAL: ${repriced_total:.6f}")
    print(f"CBBO DOWNLOAD COST GUARD: ${args.max_new_cbbo_cost:.6f}")

    if repriced_total > args.max_new_cbbo_cost + 1e-12:
        raise SystemExit(
            "ABORTED BEFORE DOWNLOAD: re-priced new CBBO cost exceeds --max-new-cbbo-cost. "
            "Increase the guard explicitly only after reviewing the estimate."
        )

    for row in plan_rows:
        day = date.fromisoformat(str(row["date"]))
        if day in repriced_costs:
            row["estimated_new_cbbo_cost"] = repriced_costs[day]

    print("PREFLIGHT PASSED: beginning CBBO-1m acquisition within the reviewed estimate guard.")

    replay_script = Path("scripts/gexy_databento_replay.py")
    if not replay_script.exists():
        raise SystemExit(f"missing replay script: {replay_script}")

    for day in args.dates:
        chain_path = _chain_path(day)
        quote_path = _quotes_path(day)
        command = [
            sys.executable,
            str(replay_script),
            "--date",
            day.isoformat(),
            "--expiration",
            day.isoformat(),
            "--chain-csv",
            str(chain_path),
            "--horizons",
            args.horizons,
        ]
        if quote_path.exists():
            command.extend(["--quotes-csv", str(quote_path)])
            print(f"\n{day.isoformat()} REPLAYING FROM CACHE: {quote_path}", flush=True)
        else:
            estimated_cost = repriced_costs[day]
            print(
                f"\n{day.isoformat()} DOWNLOADING + CACHING CBBO-1m "
                f"(re-priced estimate ${estimated_cost:.6f})",
                flush=True,
            )

        _run_with_heartbeat(command, day)

    manifest_path = Path("gexy_spxw_multiday_replay_manifest.csv")
    final_rows: list[dict[str, object]] = []
    for row in plan_rows:
        day = date.fromisoformat(str(row["date"]))
        final_rows.append(
            {
                **row,
                "quotes_cached_after_run": _quotes_path(day).exists(),
                "features_saved": _features_path(day).exists(),
            }
        )
    pd.DataFrame(final_rows).to_csv(manifest_path, index=False)

    print("\nMULTI-DAY REPLAY COMPLETE")
    print(f"DATES: {len(args.dates)}")
    print(f"RE-PRICED NEW CBBO COST USED FOR GUARD: ${repriced_total:.6f}")
    print(f"SAVED MANIFEST: {manifest_path}")
    print(
        "NOTE: The CBBO guard is a local preflight estimate guard, not a vendor transactional "
        "billing cap. Each day is cached independently; re-running after all quote CSVs exist "
        "reuses local data and incurs no new CBBO download cost."
    )


if __name__ == "__main__":
    main()
