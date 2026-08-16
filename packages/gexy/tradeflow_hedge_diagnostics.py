from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from packages.gexy.tradeflow_diagnostics import DEFAULT_SIGNAL_COLUMNS, score_flow_signals


RAW_FLOW_SIGNALS = DEFAULT_SIGNAL_COLUMNS

HEDGE_FLOW_SIGNALS = (
    "hedge_delta_units",
    "hedge_call_delta_units",
    "hedge_put_delta_units",
    "hedge_gamma_units_per_point",
    "hedge_call_gamma_units_per_point",
    "hedge_put_gamma_units_per_point",
    "hedge_gross_abs_delta_notional",
    "hedge_gross_abs_gex_notional_per_1pct",
)


def align_raw_and_hedge_frames(raw: pd.DataFrame, hedge: pd.DataFrame) -> pd.DataFrame:
    """Align raw and Greek-weighted flow on identical causal timestamps.

    Future-return labels and replay_match come from the hedge frame. Raw flow
    contributes only its signal columns, so both signal families are scored on
    the exact same availability timestamps and targets.
    """
    if "timestamp" not in raw.columns or "timestamp" not in hedge.columns:
        raise ValueError("raw and hedge frames must contain timestamp")

    left = hedge.copy()
    right = raw.copy()
    left["timestamp"] = pd.to_datetime(left["timestamp"], utc=True, errors="coerce")
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True, errors="coerce")
    left = left.dropna(subset=["timestamp"]).drop_duplicates("timestamp", keep="last")
    right = right.dropna(subset=["timestamp"]).drop_duplicates("timestamp", keep="last")

    raw_columns = ["timestamp", *[column for column in RAW_FLOW_SIGNALS if column in right.columns]]
    if len(raw_columns) == 1:
        raise ValueError("raw frame contains none of the configured flow signals")

    aligned = left.merge(
        right[raw_columns],
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )
    return aligned.sort_values("timestamp").reset_index(drop=True)


def score_raw_vs_hedge(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
) -> pd.DataFrame:
    """Score raw-flow and hedge-flow families on the same observations."""
    aligned = align_raw_and_hedge_frames(raw, hedge)

    raw_results = score_flow_signals(
        aligned,
        horizons_minutes=horizons_minutes,
        signal_columns=RAW_FLOW_SIGNALS,
    )
    hedge_results = score_flow_signals(
        aligned,
        horizons_minutes=horizons_minutes,
        signal_columns=HEDGE_FLOW_SIGNALS,
    )

    frames: list[pd.DataFrame] = []
    if not raw_results.empty:
        raw_results = raw_results.copy()
        raw_results.insert(1, "family", "raw_flow")
        frames.append(raw_results)
    if not hedge_results.empty:
        hedge_results = hedge_results.copy()
        hedge_results.insert(1, "family", "hedge_flow")
        frames.append(hedge_results)
    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True, sort=False)
    return result.sort_values(
        ["horizon_minutes", "family", "abs_spearman"],
        ascending=[True, True, False],
        na_position="last",
    ).reset_index(drop=True)


def best_family_rows(results: pd.DataFrame) -> pd.DataFrame:
    """Return the strongest absolute-Spearman signal in each family/horizon."""
    if results.empty:
        return results.copy()
    ordered = results.sort_values(
        ["horizon_minutes", "family", "abs_spearman"],
        ascending=[True, True, False],
        na_position="last",
    )
    return ordered.groupby(["horizon_minutes", "family"], sort=True, as_index=False).head(1).reset_index(drop=True)
