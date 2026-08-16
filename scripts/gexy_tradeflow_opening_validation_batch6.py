from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import partial_spearman
from packages.gexy.tradeflow_hedge_robustness import matched_with_coverage
from packages.gexy.tradeflow_multiday_validation import (
    MOMENTUM_SIGNAL,
    PRIMARY_HEDGE_SIGNAL,
    PRIMARY_RAW_SIGNAL,
)
from packages.gexy.tradeflow_window_regime import assign_session_window


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_MIN_VOLUME_COVERAGE = 0.90
FROZEN_HORIZON = 15
TARGET = "forward_return_15m_bps"


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


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def _spearman(signal: pd.Series, target: pd.Series) -> float:
    frame = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "target": pd.to_numeric(target, errors="coerce"),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return float("nan")
    return float(
        frame["signal"].rank(method="average").corr(
            frame["target"].rank(method="average"), method="pearson"
        )
    )


def _truthy(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _median_numeric(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns:
        return float("nan")
    values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return float(values.median()) if len(values) else float("nan")


def _evaluate_day(
    day: str,
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    min_volume_coverage: float,
) -> dict[str, object]:
    sample = matched_with_coverage(raw, hedge, min_volume_coverage=min_volume_coverage)
    sample = assign_session_window(sample)
    sample = sample.loc[sample["session_window"] == "opening"].copy()

    required = [PRIMARY_HEDGE_SIGNAL, PRIMARY_RAW_SIGNAL, MOMENTUM_SIGNAL, TARGET]
    missing = [column for column in required if column not in sample.columns]
    if missing:
        raise ValueError(f"{day}: validation sample missing columns: {', '.join(missing)}")

    complete = sample[required].apply(pd.to_numeric, errors="coerce")
    complete = complete.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
    if len(complete) < 3:
        raise ValueError(f"{day}: fewer than 3 complete frozen opening 15m observations")

    _, endpoint_a = partial_spearman(
        complete[PRIMARY_HEDGE_SIGNAL],
        complete[TARGET],
        complete[[MOMENTUM_SIGNAL, PRIMARY_RAW_SIGNAL]],
    )
    _, partial_momentum = partial_spearman(
        complete[PRIMARY_HEDGE_SIGNAL],
        complete[TARGET],
        complete[[MOMENTUM_SIGNAL]],
    )
    _, partial_raw = partial_spearman(
        complete[PRIMARY_HEDGE_SIGNAL],
        complete[TARGET],
        complete[[PRIMARY_RAW_SIGNAL]],
    )
    endpoint_b = _spearman(complete[PRIMARY_HEDGE_SIGNAL], complete[TARGET])

    hedge_raw = _spearman(complete[PRIMARY_HEDGE_SIGNAL], complete[PRIMARY_RAW_SIGNAL])
    hedge_momentum = _spearman(complete[PRIMARY_HEDGE_SIGNAL], complete[MOMENTUM_SIGNAL])
    raw_momentum = _spearman(complete[PRIMARY_RAW_SIGNAL], complete[MOMENTUM_SIGNAL])

    quality = assign_session_window(hedge)
    quality = quality.loc[quality["session_window"] == "opening"].copy()
    if "replay_match" in quality.columns:
        replay_mask = _truthy(quality["replay_match"])
        replay_quality = quality.loc[replay_mask].copy()
        replay_matches = int(replay_mask.sum())
    else:
        replay_quality = quality.copy()
        replay_matches = len(quality)

    return {
        "trading_day": day,
        "horizon_minutes": FROZEN_HORIZON,
        "observations": int(len(complete)),
        "endpoint_a_partial_momentum_raw": float(endpoint_a),
        "endpoint_a_negative": bool(np.isfinite(endpoint_a) and endpoint_a < 0),
        "endpoint_a_positive": bool(np.isfinite(endpoint_a) and endpoint_a > 0),
        "endpoint_b_ordinary_spearman": float(endpoint_b),
        "endpoint_b_negative": bool(np.isfinite(endpoint_b) and endpoint_b < 0),
        "endpoint_b_positive": bool(np.isfinite(endpoint_b) and endpoint_b > 0),
        "hedge_partial_controlling_momentum": float(partial_momentum),
        "hedge_partial_controlling_raw": float(partial_raw),
        "hedge_raw_spearman": float(hedge_raw),
        "hedge_momentum_spearman": float(hedge_momentum),
        "raw_momentum_spearman": float(raw_momentum),
        "opening_replay_matches": replay_matches,
        "opening_replay_rows": int(len(quality)),
        "median_symbol_minute_greek_solve_rate": _median_numeric(
            replay_quality, "hedge_greek_solved_pct"
        ),
        "median_classified_volume_with_greeks": _median_numeric(
            replay_quality, "hedge_greek_solved_contract_volume_pct"
        ),
    }


def _summarize(per_day: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for endpoint, column in (
        ("A_historical_two_control", "endpoint_a_partial_momentum_raw"),
        ("B_ordinary_heterogeneity", "endpoint_b_ordinary_spearman"),
    ):
        values = pd.to_numeric(per_day[column], errors="coerce").dropna()
        rows.append(
            {
                "endpoint": endpoint,
                "horizon_minutes": FROZEN_HORIZON,
                "days": int(len(values)),
                "negative_days": int((values < 0).sum()),
                "positive_days": int((values > 0).sum()),
                "zero_days": int((values == 0).sum()),
                "median_spearman": float(values.median()) if len(values) else np.nan,
                "min_spearman": float(values.min()) if len(values) else np.nan,
                "max_spearman": float(values.max()) if len(values) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen GEXY Batch-6 opening-window heterogeneity replication from local feature CSVs. "
            "This validator is 15m only: Endpoint A is the historical momentum+raw partial Spearman; "
            "Endpoint B is the ordinary hedge/return heterogeneity endpoint. No alternate horizon, regime split, "
            "or market-data request is made."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--min-volume-coverage",
        type=float,
        default=DEFAULT_MIN_VOLUME_COVERAGE,
        help="minimum classified contract volume with usable Greeks; frozen Batch-6 value: 0.90",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing local raw-flow and hedge-flow feature CSVs",
    )
    args = parser.parse_args()
    if not 0.0 <= args.min_volume_coverage <= 1.0:
        parser.error("--min-volume-coverage must be between 0 and 1")

    rows: list[dict[str, object]] = []
    for day in args.dates:
        raw_path = _raw_path(args.data_dir, day)
        hedge_path = _hedge_path(args.data_dir, day)
        if not raw_path.exists():
            raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
        if not hedge_path.exists():
            raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")
        try:
            rows.append(
                _evaluate_day(
                    day,
                    pd.read_csv(raw_path),
                    pd.read_csv(hedge_path),
                    min_volume_coverage=args.min_volume_coverage,
                )
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    per_day = pd.DataFrame(rows)
    summary = _summarize(per_day)

    by_day_output = args.data_dir / "gexy_spxw_tradeflow_opening_validation_batch_6_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_tradeflow_opening_validation_batch_6_summary.csv"
    args.data_dir.mkdir(parents=True, exist_ok=True)
    per_day.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)

    print("GEXY OPENING-WINDOW VALIDATION BATCH 6 — FROZEN 15M HETEROGENEITY REPLICATION")
    print(f"DATES: {','.join(args.dates)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print("HORIZON: 15 minutes only")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("ENDPOINT A: hedge_delta_units partial Spearman controlling backward 1m return + raw signed contracts; historical continuity")
    print("ENDPOINT B: ordinary hedge_delta_units vs 15m forward return Spearman; heterogeneity endpoint with no assumed dominant sign")
    print("STATUS: fresh untouched Batch-6 heterogeneity replication; endpoints were frozen before acquisition")

    display_columns = [
        "trading_day",
        "observations",
        "endpoint_a_partial_momentum_raw",
        "endpoint_a_negative",
        "endpoint_a_positive",
        "endpoint_b_ordinary_spearman",
        "endpoint_b_negative",
        "endpoint_b_positive",
        "hedge_partial_controlling_momentum",
        "hedge_partial_controlling_raw",
        "hedge_raw_spearman",
        "hedge_momentum_spearman",
        "raw_momentum_spearman",
        "opening_replay_matches",
        "opening_replay_rows",
        "median_symbol_minute_greek_solve_rate",
        "median_classified_volume_with_greeks",
    ]
    print("\nDAY-BY-DAY BATCH-6 RESULTS")
    print(per_day[display_columns].to_string(index=False))
    print("\nSEPARATE ENDPOINT SIGN / MAGNITUDE SUMMARY")
    print(summary.to_string(index=False))
    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print("NO PAID DATA REQUESTS: this validator reads only existing local causal feature CSVs.")
    print("INTERPRETATION LIMIT: hedge_delta_units is a liquidity-provider hedge proxy; heterogeneity/correlation is not dealer inventory, causality, or a production-edge claim.")


if __name__ == "__main__":
    main()
