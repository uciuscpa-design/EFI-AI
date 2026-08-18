from __future__ import annotations

from collections.abc import Collection, Iterable

import numpy as np
import pandas as pd

from packages.gexy.replay import add_forward_horizon_labels


OFF_EXCHANGE_FEATURES = (
    "offx_trade_records",
    "offx_unique_symbols",
    "offx_share_volume",
    "offx_notional",
    "offx_mean_print_size",
    "offx_max_print_size",
    "offx_large_print_records",
    "offx_large_print_volume",
    "offx_large_print_notional",
    "offx_large_print_volume_share",
    "offx_repeated_level_groups",
    "offx_repeated_level_volume",
    "offx_repeated_level_volume_share",
    "offx_volume_anomaly_z",
    "offx_notional_anomaly_z",
    "offx_large_print_volume_anomaly_z",
    "off_exchange_anomaly_score",
)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def normalize_off_exchange_trades(
    raw: pd.DataFrame,
    *,
    available_at_col: str,
    symbol_col: str,
    price_col: str,
    size_col: str,
    venue_col: str | None = None,
    off_exchange_col: str | None = None,
    off_exchange_venues: Collection[object] | None = None,
    source: str = "unknown",
) -> pd.DataFrame:
    """Normalize deterministically identified off-exchange/TRF equity trades.

    GEXY deliberately does not guess that a print is off-exchange from its size,
    price, or generic condition codes. The caller must provide either:

    1. a boolean-like ``off_exchange_col`` supplied by the source adapter; or
    2. ``venue_col`` plus an explicit allow-list of off-exchange/TRF venue values.

    ``available_at_col`` must be the timestamp at which the print was actually
    observable to the strategy/research process (for example, a receive or SIP
    dissemination timestamp). This preserves delayed-report causality.

    The normalized frame intentionally contains no buyer/seller identity and no
    directional-intent inference. Off-exchange does not imply informed trading.
    """
    required = {available_at_col, symbol_col, price_col, size_col}
    if venue_col is not None:
        required.add(venue_col)
    if off_exchange_col is not None:
        required.add(off_exchange_col)
    missing = sorted(column for column in required if column not in raw.columns)
    if missing:
        raise ValueError(f"off-exchange frame missing required columns: {', '.join(missing)}")

    if off_exchange_col is None and (venue_col is None or off_exchange_venues is None):
        raise ValueError(
            "off-exchange identification must be explicit: provide off_exchange_col or "
            "venue_col with off_exchange_venues"
        )

    frame = raw.copy()
    frame[available_at_col] = pd.to_datetime(frame[available_at_col], utc=True, errors="coerce")
    frame[price_col] = pd.to_numeric(frame[price_col], errors="coerce")
    frame[size_col] = pd.to_numeric(frame[size_col], errors="coerce")
    frame[symbol_col] = frame[symbol_col].astype("string")

    if off_exchange_col is not None:
        marker = frame[off_exchange_col]
        if pd.api.types.is_bool_dtype(marker.dtype):
            is_off_exchange = marker.fillna(False)
        else:
            normalized = marker.astype("string").str.strip().str.lower()
            is_off_exchange = normalized.isin({"1", "true", "t", "yes", "y", "off_exchange", "trf"})
    else:
        assert venue_col is not None
        assert off_exchange_venues is not None
        allowed = {str(value).strip().upper() for value in off_exchange_venues}
        venue_values = frame[venue_col].astype("string").str.strip().str.upper()
        is_off_exchange = venue_values.isin(allowed)

    frame = frame.loc[is_off_exchange].copy()
    frame = frame.dropna(subset=[available_at_col, symbol_col, price_col, size_col])
    frame = frame.loc[(frame[price_col] > 0) & (frame[size_col] > 0)].copy()
    if frame.empty:
        columns = [
            "available_at",
            "symbol",
            "price",
            "size",
            "notional",
            "reporting_venue",
            "source",
            "off_exchange_observed",
        ]
        return pd.DataFrame(columns=columns)

    normalized = pd.DataFrame(
        {
            "available_at": frame[available_at_col],
            "symbol": frame[symbol_col].astype(str),
            "price": frame[price_col].astype(float),
            "size": frame[size_col].astype(float),
            "source": source,
            "off_exchange_observed": True,
        }
    )
    if venue_col is None:
        normalized["reporting_venue"] = "explicit_flag"
    else:
        normalized["reporting_venue"] = frame[venue_col].astype(str).values
    normalized["notional"] = normalized["price"] * normalized["size"]

    return normalized.sort_values(["available_at", "symbol", "price"]).reset_index(drop=True)


def add_causal_large_print_flags(
    trades: pd.DataFrame,
    *,
    lookback_prints: int = 200,
    min_periods: int = 30,
    quantile: float = 0.95,
) -> pd.DataFrame:
    """Flag unusually large prints using only prior prints in the same symbol.

    The current print is excluded from its own baseline with ``shift(1)``.
    Until enough prior prints exist, ``large_print_eligible`` is false and the
    print cannot be classified as large. This is an anomaly label, not a claim
    about participant identity, information content, or trade direction.
    """
    if lookback_prints < 1:
        raise ValueError("lookback_prints must be positive")
    if min_periods < 1 or min_periods > lookback_prints:
        raise ValueError("min_periods must be between 1 and lookback_prints")
    if not 0 < quantile < 1:
        raise ValueError("quantile must be between 0 and 1")

    required = {"available_at", "symbol", "size", "notional", "price"}
    missing = sorted(required.difference(trades.columns))
    if missing:
        raise ValueError(f"normalized off-exchange frame missing columns: {', '.join(missing)}")

    frame = trades.copy()
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True, errors="coerce")
    frame["size"] = pd.to_numeric(frame["size"], errors="coerce")
    frame = frame.dropna(subset=["available_at", "symbol", "size"]).copy()
    frame = frame.sort_values(["symbol", "available_at"]).reset_index(drop=True)

    thresholds = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, index in frame.groupby("symbol", sort=False).groups.items():
        index = list(index)
        prior = frame.loc[index, "size"].shift(1)
        threshold = prior.rolling(lookback_prints, min_periods=min_periods).quantile(quantile)
        thresholds.loc[index] = threshold.to_numpy()

    frame["large_print_threshold"] = thresholds
    frame["large_print_eligible"] = frame["large_print_threshold"].notna()
    frame["is_large_print"] = frame["large_print_eligible"] & (
        frame["size"] >= frame["large_print_threshold"]
    )
    frame["large_print_size_ratio"] = frame["size"] / frame["large_print_threshold"]
    frame.loc[~frame["large_print_eligible"], "large_print_size_ratio"] = np.nan
    return frame.sort_values("available_at").reset_index(drop=True)


def _causal_robust_z(
    values: pd.Series,
    *,
    lookback: int,
    min_periods: int,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    prior = numeric.shift(1)
    median = prior.rolling(lookback, min_periods=min_periods).median()
    abs_dev = (prior - median).abs()
    mad = abs_dev.rolling(lookback, min_periods=min_periods).median()
    scale = 1.4826 * mad
    z = (numeric - median) / scale
    return z.where(scale > 0)


def aggregate_completed_minute_off_exchange(
    trades: pd.DataFrame,
    *,
    anomaly_lookback_minutes: int = 120,
    anomaly_min_periods: int = 30,
) -> pd.DataFrame:
    """Aggregate off-exchange prints into strictly causal completed-minute features.

    Prints observable during minute M are stamped M+1, so the completed minute is
    not available until it has finished. Repeated levels are exact symbol/price
    repeats within the completed minute. Anomaly scores are non-directional and
    are calculated only against prior completed minutes.
    """
    if anomaly_lookback_minutes < 1:
        raise ValueError("anomaly_lookback_minutes must be positive")
    if anomaly_min_periods < 1 or anomaly_min_periods > anomaly_lookback_minutes:
        raise ValueError("anomaly_min_periods must be between 1 and anomaly_lookback_minutes")

    required = {
        "available_at",
        "symbol",
        "price",
        "size",
        "notional",
        "is_large_print",
        "large_print_eligible",
    }
    missing = sorted(required.difference(trades.columns))
    if missing:
        raise ValueError(f"off-exchange trade frame missing columns: {', '.join(missing)}")

    frame = trades.copy()
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True, errors="coerce")
    for column in ("price", "size", "notional"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["available_at", "symbol", "price", "size", "notional"]).copy()
    if frame.empty:
        raise ValueError("off-exchange trade frame contains no usable prints")

    frame["offx_minute"] = frame["available_at"].dt.floor("min")
    rows: list[dict[str, object]] = []
    for minute, group in frame.groupby("offx_minute", sort=True):
        large = group.loc[group["is_large_print"]]
        repeated = (
            group.groupby(["symbol", "price"], dropna=False, sort=False)
            .agg(records=("size", "size"), volume=("size", "sum"))
            .reset_index()
        )
        repeated = repeated.loc[repeated["records"] >= 2]
        repeated_volume = float(repeated["volume"].sum()) if not repeated.empty else 0.0
        total_volume = float(group["size"].sum())
        minute_timestamp = pd.Timestamp(minute).as_unit("ns")
        rows.append(
            {
                "offx_minute": minute_timestamp,
                "timestamp": minute_timestamp + pd.Timedelta(1, unit="min"),
                "offx_trade_records": int(len(group)),
                "offx_unique_symbols": int(group["symbol"].nunique()),
                "offx_share_volume": total_volume,
                "offx_notional": float(group["notional"].sum()),
                "offx_mean_print_size": float(group["size"].mean()),
                "offx_max_print_size": float(group["size"].max()),
                "offx_large_print_records": int(len(large)),
                "offx_large_print_volume": float(large["size"].sum()),
                "offx_large_print_notional": float(large["notional"].sum()),
                "offx_large_print_volume_share": _safe_ratio(float(large["size"].sum()), total_volume),
                "offx_large_print_eligible_records": int(group["large_print_eligible"].sum()),
                "offx_repeated_level_groups": int(len(repeated)),
                "offx_repeated_level_volume": repeated_volume,
                "offx_repeated_level_volume_share": _safe_ratio(repeated_volume, total_volume),
            }
        )

    result = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    result["offx_volume_anomaly_z"] = _causal_robust_z(
        result["offx_share_volume"],
        lookback=anomaly_lookback_minutes,
        min_periods=anomaly_min_periods,
    )
    result["offx_notional_anomaly_z"] = _causal_robust_z(
        result["offx_notional"],
        lookback=anomaly_lookback_minutes,
        min_periods=anomaly_min_periods,
    )
    result["offx_large_print_volume_anomaly_z"] = _causal_robust_z(
        result["offx_large_print_volume"],
        lookback=anomaly_lookback_minutes,
        min_periods=anomaly_min_periods,
    )
    anomaly_columns = [
        "offx_volume_anomaly_z",
        "offx_notional_anomaly_z",
        "offx_large_print_volume_anomaly_z",
    ]
    result["off_exchange_anomaly_score"] = result[anomaly_columns].abs().max(axis=1, skipna=True)
    result.loc[result[anomaly_columns].isna().all(axis=1), "off_exchange_anomaly_score"] = np.nan
    return result


def join_off_exchange_to_replay(
    off_exchange: pd.DataFrame,
    replay: pd.DataFrame,
    *,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
) -> pd.DataFrame:
    """Join completed-minute off-exchange features to replay state and future labels."""
    if "timestamp" not in off_exchange.columns:
        raise ValueError("off-exchange frame must contain timestamp")
    if "timestamp" not in replay.columns or "forward" not in replay.columns:
        raise ValueError("replay frame must contain timestamp and forward")

    left = off_exchange.copy()
    left["timestamp"] = pd.to_datetime(left["timestamp"], utc=True, errors="coerce")
    left = left.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    right = replay.copy()
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True, errors="coerce")
    right = right.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    right = add_forward_horizon_labels(right, horizons_minutes)

    merged = left.merge(right, on="timestamp", how="left", validate="one_to_one", indicator=True)
    merged["replay_match"] = merged["_merge"] == "both"
    merged = merged.drop(columns=["_merge"])
    return merged.sort_values("timestamp").reset_index(drop=True)
