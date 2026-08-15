from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


_CHANGE_COLUMNS = (
    "forward",
    "total_gax_forward_proxy_per_point",
    "total_unsigned_gex_forward_proxy_per_1pct",
    "heuristic_signed_gex_forward_proxy_per_1pct",
    "strongest_unsigned_wall",
    "strongest_positive_heuristic_wall",
    "strongest_negative_heuristic_wall",
)


def add_change_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add one-observation changes to a timestamped replay frame."""
    if "timestamp" not in frame.columns:
        raise ValueError("replay frame must contain timestamp")

    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
    result = result.sort_values("timestamp").reset_index(drop=True)

    for column in _CHANGE_COLUMNS:
        if column in result.columns:
            result[f"d_{column}"] = pd.to_numeric(result[column], errors="coerce").diff()

    if "forward" in result.columns:
        previous = pd.to_numeric(result["forward"], errors="coerce").shift(1)
        current = pd.to_numeric(result["forward"], errors="coerce")
        # This is known at the current timestamp (t-1 -> t), so keep its name
        # explicitly backward-looking. Future labels use forward_return_* names.
        result["backward_return_1m_bps"] = (current / previous - 1.0) * 10_000.0

    if "total_unsigned_gex_forward_proxy_per_1pct" in result.columns:
        previous = pd.to_numeric(
            result["total_unsigned_gex_forward_proxy_per_1pct"], errors="coerce"
        ).shift(1)
        current = pd.to_numeric(
            result["total_unsigned_gex_forward_proxy_per_1pct"], errors="coerce"
        )
        result["unsigned_gex_change_1m_pct"] = (current / previous - 1.0) * 100.0

    return result


def add_forward_horizon_labels(
    frame: pd.DataFrame,
    horizons_minutes: Iterable[int],
) -> pd.DataFrame:
    """Attach exact-clock forward-return labels for backtesting.

    Labels are only filled when the exact future minute exists in the replay.
    This avoids silently changing a requested horizon when a minute is missing.
    """
    if "timestamp" not in frame.columns or "forward" not in frame.columns:
        raise ValueError("replay frame must contain timestamp and forward")

    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
    result = result.sort_values("timestamp").reset_index(drop=True)

    forward_by_time = {
        timestamp: float(forward)
        for timestamp, forward in zip(
            result["timestamp"],
            pd.to_numeric(result["forward"], errors="coerce"),
            strict=False,
        )
        if pd.notna(forward)
    }

    for raw_horizon in horizons_minutes:
        horizon = int(raw_horizon)
        if horizon < 1:
            raise ValueError("forecast horizons must be positive minutes")
        future_values = [
            forward_by_time.get(timestamp + pd.Timedelta(minutes=horizon))
            for timestamp in result["timestamp"]
        ]
        future = pd.Series(future_values, index=result.index, dtype="float64")
        current = pd.to_numeric(result["forward"], errors="coerce")
        result[f"forward_t_plus_{horizon}m"] = future
        result[f"forward_move_{horizon}m_points"] = future - current
        result[f"forward_return_{horizon}m_bps"] = (future / current - 1.0) * 10_000.0

    return result