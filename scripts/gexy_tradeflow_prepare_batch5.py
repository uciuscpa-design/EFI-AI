from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
FROZEN_WINDOW = "09:30-10:00"
FROZEN_HORIZON = "15"
FROZEN_STRIKE_BAND = "200"


def _parse_dates(value: str) -> tuple[str, ...]:
    dates: list[str] = []
    seen: set[str] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            parsed = pd.Timestamp(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates") from exc
        if parsed.strftime("%Y-%m-%d") != item:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates")
        if item not in seen:
            seen.add(item)
            dates.append(item)
    if not dates:
        raise argparse.ArgumentTypeError("--dates must contain at least one YYYY-MM-DD date")
    return tuple(dates)


def _required_inputs(data_dir: Path, day: str) -> tuple[Path, ...]:
    return (
        Path(f"gexy_spxw_{day}_0dte_oi.csv"),
        Path(f"gexy_spxw_{day}_replay_features.csv"),
        data_dir / f"gexy_spxw_{day}_0930_1000_tcbbo.dbn.zst",
    )


def _commands(day: str, data_dir: Path) -> tuple[tuple[str, list[str]], ...]:
    python = sys.executable
    return (
        (
            "extract",
            [
                python,
                "scripts/gexy_tradeflow_extract.py",
                "--date",
                day,
                "--windows",
                FROZEN_WINDOW,
                "--strike-band-points",
                FROZEN_STRIKE_BAND,
                "--data-dir",
                str(data_dir),
            ],
        ),
        (
            "raw_features",
            [
                python,
                "scripts/gexy_tradeflow_features.py",
                "--date",
                day,
                "--windows",
                FROZEN_WINDOW,
                "--horizons",
                FROZEN_HORIZON,
                "--data-dir",
                str(data_dir),
            ],
        ),
        (
            "hedge_features",
            [
                python,
                "scripts/gexy_tradeflow_hedge_features.py",
                "--date",
                day,
                "--windows",
                FROZEN_WINDOW,
                "--horizons",
                FROZEN_HORIZON,
                "--data-dir",
                str(data_dir),
            ],
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare frozen GEXY Batch-5 opening-window local feature files for all supplied dates. "
            "The wrapper is fixed to 09:30-10:00, +/-200 points, and 15m labels. It reads only "
            "already acquired local TCBBO/replay/chain caches and does not evaluate validation endpoints."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing acquired TCBBO and generated local trade-flow files",
    )
    args = parser.parse_args()

    missing: list[str] = []
    for day in args.dates:
        for path in _required_inputs(args.data_dir, day):
            if not path.exists():
                missing.append(str(path))
    if missing:
        raise SystemExit("BATCH-5 PREP ABORTED: missing required local inputs: " + ", ".join(missing))

    args.data_dir.mkdir(parents=True, exist_ok=True)
    print("GEXY BATCH-5 LOCAL PREPARATION")
    print(f"DATES: {','.join(args.dates)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print("STRIKE BAND: opening-forward +/-200 SPX points")
    print("HORIZON LABEL: 15 minutes only")
    print("ENDPOINT EVALUATION: disabled in this wrapper")

    for day in args.dates:
        log_path = args.data_dir / f"gexy_spxw_{day}_batch5_prepare.log"
        log_parts: list[str] = []
        print(f"\n{day} PREPARATION START")
        for stage, command in _commands(day, args.data_dir):
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            log_parts.append(f"===== {stage} STDOUT =====\n{result.stdout}\n")
            if result.stderr:
                log_parts.append(f"===== {stage} STDERR =====\n{result.stderr}\n")
            if result.returncode != 0:
                log_path.write_text("\n".join(log_parts), encoding="utf-8")
                raise SystemExit(
                    f"{day} {stage} FAILED with exit code {result.returncode}; see {log_path}"
                )
            print(f"{day} {stage}: OK")
        log_path.write_text("\n".join(log_parts), encoding="utf-8")
        print(f"{day} PREPARATION COMPLETE -> {log_path}")

    print("\nBATCH-5 LOCAL PREPARATION COMPLETE")
    print(f"DATES PREPARED: {len(args.dates)}")
    print("NO PAID DATA REQUESTS: all stages read only existing local caches.")
    print("NO VALIDATION ENDPOINTS EVALUATED: run the frozen Batch-5 validator separately after preparation.")


if __name__ == "__main__":
    main()
