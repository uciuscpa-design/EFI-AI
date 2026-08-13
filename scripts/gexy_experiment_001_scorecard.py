from __future__ import annotations

import argparse
from pathlib import Path

from packages.gexy.recording import JsonlRecorder
from packages.gexy.scorecard import build_scorecard

DEFAULT_INPUT = Path("projects/gexy/experiments/experiment_001_intraday.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description="Score GEXY Experiment 001 without temporal leakage")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--min-samples", type=int, default=15)
    args = parser.parse_args()

    recorder = JsonlRecorder(args.input)
    snapshots = list(recorder.read())
    if not snapshots:
        print(f"No captured observations found: {args.input}")
        return 2

    cards = build_scorecard(snapshots, alpha=args.alpha, min_samples=args.min_samples)
    print(f"GEXY Experiment 001 scorecard | observations={len(snapshots)}")
    print("horizon  samples  train  valid  test  direction  MAE_pts  bias_pts  brier   status")
    for card in cards:
        direction = "-" if card.directional_accuracy is None else f"{card.directional_accuracy:.3f}"
        mae = "-" if card.mean_absolute_error is None else f"{card.mean_absolute_error:.3f}"
        bias = "-" if card.mean_bias is None else f"{card.mean_bias:.3f}"
        brier = "-" if card.brier_score is None else f"{card.brier_score:.3f}"
        print(
            f"{card.horizon_minutes:>4}m  {card.samples:>7}  {card.train_samples:>5}  "
            f"{card.validation_samples:>5}  {card.test_samples:>4}  {direction:>9}  "
            f"{mae:>7}  {bias:>8}  {brier:>5}   {card.status}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
