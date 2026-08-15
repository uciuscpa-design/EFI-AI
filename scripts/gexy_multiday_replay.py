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
    days = tuple(sorted({date.fromisoformat(item.strip()) for item in value.split(",") if item.strip()}))
    if not days:
        raise argparse.ArgumentTypeError("--dates must contain at least one ISO date")
    return days


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
            "Run multiple cached-or-download SPXW 0DTE replays with a preflight Databento cost guard. "
            "Without --download, only exact-symbol CBBO costs are estimated. With --download, cached "
            "quote days are replayed offline and missing quote days are downloaded only if the total "
            "estimated new CBBO cost is within --max-new-cbbo-cost."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--horizons", default="1,5,15,30,60")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--max-new-cbbo-cost", type=float, default=0.25)
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
    total_new_cost = 0.0

    for day in args.dates:
        chain_path = _chain_path(day)
        if not chain_path.exists():
            raise SystemExit(f"missing chain CSV: {chain_path}")
        chain = pd.read_csv(chain_path)
        if "raw_symbol" not in chain.columns:
            raise SystemExit(f"chain CSV missing raw_symbol: {chain_path}")

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
        print("NO MARKET DATA DOWNLOADED. Re-run with --download to execute within the cost guard.")
        return

    if total_new_cost > args.max_new_cbbo_cost + 1e-12:
        raise SystemExit(
            "ABORTED: estimated new CBBO cost exceeds --max-new-cbbo-cost. "
            "Increase the guard explicitly only after reviewing the estimate."
        )

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
            estimated_cost = next(
                row["estimated_new_cbbo_cost"]
                for row in plan_rows
                if row["date"] == day.isoformat()
            )
            print(
                f"\n{day.isoformat()} DOWNLOADING + CACHING CBBO-1m "
                f"(estimated ${estimated_cost:.6f})",
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
    print(f"ESTIMATED NEW CBBO COST USED FOR GUARD: ${total_new_cost:.6f}")
    print(f"SAVED MANIFEST: {manifest_path}")
    print(
        "NOTE: Each day is cached independently. Re-running this batch after all quote CSVs exist "
        "reuses local data and incurs no new CBBO download cost."
    )


if __name__ == "__main__":
    main()
