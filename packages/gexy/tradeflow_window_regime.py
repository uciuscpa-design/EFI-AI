from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import partial_spearman
from packages.gexy.tradeflow_hedge_robustness import matched_with_coverage
from packages.gexy.tradeflow_multiday_validation import (
    MOMENTUM_SIGNAL,
    PRIMARY_HEDGE_SIGNAL,
    PRIMARY_HORIZONS,
    PRIMARY_RAW_SIGNAL,
)


SESSION_WINDOWS = ("opening", "closing")
NEW_YORK_TZ = "America/New_York"


def _spearman(signal: pd.Series, target: pd.Series) -> tuple[int, float]:
    frame = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "target": pd.to_numeric(target, errors="coerce"),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return len(frame), float("nan")
    value = frame["signal"].rank(method="average").corr(
        frame["target"].rank(method="average"), method="pearson"
    )
    return len(frame), float(value)


def assign_session_window(frame: pd.DataFrame) -> pd.DataFrame:
    """Label rows by the two already purchased GEXY intraday windows.

    The label is based on ``flow_minute`` in America/New_York so feature
    availability at M+1 does not move a 09:59 or 15:59 trade minute into a
    different window.
    """
    result = frame.copy()
    if "flow_minute" in result.columns:
        flow_minute = pd.to_datetime(result["flow_minute"], utc=True, errors="coerce")
    elif "timestamp" in result.columns:
        availability = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
        flow_minute = availability - pd.Timedelta(minutes=1)
    else:
        raise ValueError("frame must contain flow_minute or timestamp")

    local = flow_minute.dt.tz_convert(NEW_YORK_TZ)
    minute_of_day = local.dt.hour * 60 + local.dt.minute
    labels = pd.Series(pd.NA, index=result.index, dtype="string")
    labels.loc[(minute_of_day >= 9 * 60 + 30) & (minute_of_day < 10 * 60)] = "opening"
    labels.loc[(minute_of_day >= 15 * 60 + 30) & (minute_of_day < 16 * 60)] = "closing"
    result["session_window"] = labels
    return result


def evaluate_window_day(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    trading_day: str,
    min_volume_coverage: float = 0.90,
    horizons_minutes: Iterable[int] = PRIMARY_HORIZONS,
) -> pd.DataFrame:
    """Score the unchanged net-delta endpoint separately in opening and closing windows."""
    sample = matched_with_coverage(raw, hedge, min_volume_coverage=min_volume_coverage)
    sample = assign_session_window(sample)
    rows: list[dict[str, object]] = []

    for window in SESSION_WINDOWS:
        window_frame = sample.loc[sample["session_window"] == window].copy()
        for raw_horizon in horizons_minutes:
            horizon = int(raw_horizon)
            target_column = f"forward_return_{horizon}m_bps"
            required = {
                PRIMARY_HEDGE_SIGNAL,
                PRIMARY_RAW_SIGNAL,
                MOMENTUM_SIGNAL,
                target_column,
            }
            if not required.issubset(window_frame.columns):
                continue

            observations, hedge_partial = partial_spearman(
                window_frame[PRIMARY_HEDGE_SIGNAL],
                window_frame[target_column],
                window_frame[[MOMENTUM_SIGNAL, PRIMARY_RAW_SIGNAL]],
            )
            _, raw_partial = partial_spearman(
                window_frame[PRIMARY_RAW_SIGNAL],
                window_frame[target_column],
                window_frame[[MOMENTUM_SIGNAL]],
            )
            _, hedge_spearman = _spearman(
                window_frame[PRIMARY_HEDGE_SIGNAL], window_frame[target_column]
            )
            _, momentum_spearman = _spearman(
                window_frame[MOMENTUM_SIGNAL], window_frame[target_column]
            )

            rows.append(
                {
                    "trading_day": str(trading_day),
                    "session_window": window,
                    "horizon_minutes": horizon,
                    "observations": int(observations),
                    "momentum_spearman": momentum_spearman,
                    "raw_partial_spearman_controlling_momentum": raw_partial,
                    "hedge_spearman": hedge_spearman,
                    "hedge_partial_spearman_controlling_momentum_and_raw": hedge_partial,
                    "negative_sign": bool(np.isfinite(hedge_partial) and hedge_partial < 0),
                }
            )

    return pd.DataFrame(rows)


def summarize_window_days(per_day: pd.DataFrame) -> pd.DataFrame:
    """Summarize exploratory sign stability by pre-existing acquisition window."""
    if per_day.empty:
        return per_day.copy()
    value_column = "hedge_partial_spearman_controlling_momentum_and_raw"
    rows: list[dict[str, object]] = []
    grouped = per_day.groupby(["session_window", "horizon_minutes"], sort=True)
    for (window, horizon), group in grouped:
        values = pd.to_numeric(group[value_column], errors="coerce").dropna()
        rows.append(
            {
                "session_window": str(window),
                "horizon_minutes": int(horizon),
                "days": int(len(values)),
                "negative_days": int((values < 0).sum()),
                "negative_day_pct": float((values < 0).mean()) if len(values) else np.nan,
                "median_partial_spearman": float(values.median()) if len(values) else np.nan,
                "min_partial_spearman": float(values.min()) if len(values) else np.nan,
                "max_partial_spearman": float(values.max()) if len(values) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _pooled_controls(frame: pd.DataFrame) -> pd.DataFrame:
    controls = frame[[MOMENTUM_SIGNAL, PRIMARY_RAW_SIGNAL]].copy().reset_index(drop=True)
    dummies = pd.get_dummies(
        frame["trading_day"].astype(str),
        prefix="day",
        drop_first=True,
        dtype=float,
    ).reset_index(drop=True)
    if not dummies.empty:
        controls = pd.concat([controls, dummies], axis=1)
    return controls


def pooled_window_endpoints(
    daily_frames: Iterable[tuple[str, pd.DataFrame, pd.DataFrame]],
    *,
    min_volume_coverage: float = 0.90,
    horizons_minutes: Iterable[int] = PRIMARY_HORIZONS,
) -> pd.DataFrame:
    """Pool each existing time window across days with categorical day fixed effects.

    This is explicitly post-batch exploratory analysis. It does not replace the
    frozen unconditional day-by-day primary endpoints.
    """
    pieces: list[pd.DataFrame] = []
    for trading_day, raw, hedge in daily_frames:
        sample = matched_with_coverage(raw, hedge, min_volume_coverage=min_volume_coverage)
        sample = assign_session_window(sample)
        sample["trading_day"] = str(trading_day)
        pieces.append(sample)
    if not pieces:
        return pd.DataFrame()

    pooled = pd.concat(pieces, ignore_index=True, sort=False)
    rows: list[dict[str, object]] = []
    for window in SESSION_WINDOWS:
        window_frame = pooled.loc[pooled["session_window"] == window].copy().reset_index(drop=True)
        for raw_horizon in horizons_minutes:
            horizon = int(raw_horizon)
            target_column = f"forward_return_{horizon}m_bps"
            required = {
                PRIMARY_HEDGE_SIGNAL,
                PRIMARY_RAW_SIGNAL,
                MOMENTUM_SIGNAL,
                target_column,
                "trading_day",
            }
            if not required.issubset(window_frame.columns):
                continue
            controls = _pooled_controls(window_frame)
            observations, partial = partial_spearman(
                window_frame[PRIMARY_HEDGE_SIGNAL],
                window_frame[target_column],
                controls,
            )
            rows.append(
                {
                    "session_window": window,
                    "horizon_minutes": horizon,
                    "observations": int(observations),
                    "days": int(window_frame["trading_day"].nunique()),
                    "partial_spearman_controlling_momentum_raw_and_day": partial,
                    "negative_sign": bool(np.isfinite(partial) and partial < 0),
                }
            )
    return pd.DataFrame(rows)
