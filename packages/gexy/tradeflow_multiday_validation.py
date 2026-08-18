from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import (
    partial_spearman,
    score_incremental_hedge_information,
)
from packages.gexy.tradeflow_hedge_robustness import matched_with_coverage


PRIMARY_PAIR = "net_contracts_vs_delta"
PRIMARY_HORIZONS = (5, 15)
PRIMARY_HEDGE_SIGNAL = "hedge_delta_units"
PRIMARY_RAW_SIGNAL = "flow_net_signed_contracts"
MOMENTUM_SIGNAL = "backward_return_1m_bps"


def evaluate_primary_day(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    trading_day: str,
    min_volume_coverage: float = 0.90,
    horizons_minutes: Iterable[int] = PRIMARY_HORIZONS,
) -> pd.DataFrame:
    """Return the frozen net-delta primary endpoints for one trading day."""
    results = score_incremental_hedge_information(
        raw,
        hedge,
        min_volume_coverage=min_volume_coverage,
        horizons_minutes=horizons_minutes,
    )
    if results.empty:
        return results
    primary = results.loc[results["pair"] == PRIMARY_PAIR].copy()
    wanted = {int(item) for item in horizons_minutes}
    primary = primary.loc[primary["horizon_minutes"].isin(wanted)].copy()
    primary.insert(0, "trading_day", str(trading_day))
    return primary.sort_values("horizon_minutes").reset_index(drop=True)


def summarize_primary_days(per_day: pd.DataFrame) -> pd.DataFrame:
    """Summarize sign stability of the fixed endpoint across days."""
    if per_day.empty:
        return per_day.copy()
    value_column = "hedge_partial_spearman_controlling_momentum_and_raw"
    if value_column not in per_day.columns:
        raise ValueError(f"per-day results must contain {value_column}")

    rows: list[dict[str, object]] = []
    for horizon, group in per_day.groupby("horizon_minutes", sort=True):
        values = pd.to_numeric(group[value_column], errors="coerce").dropna()
        rows.append(
            {
                "horizon_minutes": int(horizon),
                "days": int(len(values)),
                "negative_days": int((values < 0).sum()),
                "negative_day_pct": float((values < 0).mean()) if len(values) else np.nan,
                "median_partial_spearman": float(values.median()) if len(values) else np.nan,
                "min_partial_spearman": float(values.min()) if len(values) else np.nan,
                "max_partial_spearman": float(values.max()) if len(values) else np.nan,
                "all_days_negative": bool(len(values) > 0 and (values < 0).all()),
            }
        )
    return pd.DataFrame(rows)


def fixed_clock_nonoverlap_sample(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    horizon_minutes: int,
    min_volume_coverage: float = 0.90,
) -> pd.DataFrame:
    """Select deterministic clock-spaced rows so same-horizon labels do not overlap.

    Rows are retained only when the UTC epoch-minute is exactly divisible by the
    requested horizon. This is a fixed clock rule independent of returns or
    signal values. It is a post-holdout sensitivity analysis, not a replacement
    for the pre-specified full-minute primary endpoint.
    """
    horizon = int(horizon_minutes)
    if horizon < 1:
        raise ValueError("horizon_minutes must be positive")
    sample = matched_with_coverage(
        raw,
        hedge,
        min_volume_coverage=min_volume_coverage,
    )
    if sample.empty:
        return sample
    timestamps = pd.to_datetime(sample["timestamp"], utc=True, errors="coerce")
    epoch_minutes = timestamps.astype("int64") // (60 * 1_000_000_000)
    keep = timestamps.notna() & ((epoch_minutes % horizon) == 0)
    return sample.loc[keep].copy().reset_index(drop=True)


def _day_fixed_effect_controls(pooled: pd.DataFrame) -> pd.DataFrame:
    """Return momentum/raw controls plus true categorical day fixed effects."""
    controls = pooled[[MOMENTUM_SIGNAL, PRIMARY_RAW_SIGNAL]].copy()
    day_dummies = pd.get_dummies(
        pooled["trading_day"].astype(str),
        prefix="day",
        drop_first=True,
        dtype=float,
    )
    if not day_dummies.empty:
        controls = pd.concat([controls.reset_index(drop=True), day_dummies.reset_index(drop=True)], axis=1)
    return controls


def pooled_nonoverlap_primary(
    daily_frames: Iterable[tuple[str, pd.DataFrame, pd.DataFrame]],
    *,
    horizons_minutes: Iterable[int] = PRIMARY_HORIZONS,
    min_volume_coverage: float = 0.90,
) -> pd.DataFrame:
    """Pool deterministic non-overlapping rows and partial out day membership.

    Controls are the completed flow-minute SPX return, raw net signed contracts,
    and categorical day fixed effects. The day dummies remove arbitrary session
    level differences rather than assuming a linear trend across ordered days.
    """
    materialized = list(daily_frames)
    rows: list[dict[str, object]] = []
    for raw_horizon in horizons_minutes:
        horizon = int(raw_horizon)
        pieces: list[pd.DataFrame] = []
        for trading_day, raw, hedge in materialized:
            sample = fixed_clock_nonoverlap_sample(
                raw,
                hedge,
                horizon_minutes=horizon,
                min_volume_coverage=min_volume_coverage,
            )
            if sample.empty:
                continue
            sample = sample.copy()
            sample["trading_day"] = str(trading_day)
            pieces.append(sample)
        if not pieces:
            continue
        pooled = pd.concat(pieces, ignore_index=True, sort=False)
        target_column = f"forward_return_{horizon}m_bps"
        required = {
            PRIMARY_HEDGE_SIGNAL,
            PRIMARY_RAW_SIGNAL,
            MOMENTUM_SIGNAL,
            target_column,
            "trading_day",
        }
        if not required.issubset(pooled.columns):
            continue
        controls = _day_fixed_effect_controls(pooled)
        observations, partial = partial_spearman(
            pooled[PRIMARY_HEDGE_SIGNAL],
            pooled[target_column],
            controls,
        )
        rows.append(
            {
                "horizon_minutes": horizon,
                "observations": int(observations),
                "days": int(pooled["trading_day"].nunique()),
                "partial_spearman_controlling_momentum_raw_and_day": partial,
                "negative_sign": bool(np.isfinite(partial) and partial < 0),
            }
        )
    return pd.DataFrame(rows)
