from __future__ import annotations

from collections.abc import Collection

import pandas as pd

from packages.gexy.off_exchange_sources import (
    normalize_alpaca_sip_trades,
    normalize_massive_stock_trades,
)
from packages.gexy.off_exchange_streaming import enforce_live_receive_causality


def _attach_receive_time_by_trade_id(
    normalized: pd.DataFrame,
    raw: pd.DataFrame,
    *,
    raw_symbol_col: str,
    raw_trade_id_col: str,
) -> pd.DataFrame:
    if normalized.empty:
        return normalized.copy()
    required_raw = {raw_symbol_col, raw_trade_id_col, "gexy_received_at"}
    missing = sorted(required_raw.difference(raw.columns))
    if missing:
        raise ValueError(f"live raw capture missing columns: {', '.join(missing)}")
    if "vendor_trade_id" not in normalized.columns:
        raise ValueError("normalized live capture must preserve vendor_trade_id")

    receipt = pd.DataFrame(
        {
            "symbol": raw[raw_symbol_col].astype("string"),
            "vendor_trade_id": raw[raw_trade_id_col].astype("string"),
            "gexy_received_at": pd.to_datetime(raw["gexy_received_at"], utc=True, errors="coerce"),
        }
    ).dropna(subset=["symbol", "vendor_trade_id", "gexy_received_at"])
    receipt = (
        receipt.groupby(["symbol", "vendor_trade_id"], as_index=False, sort=False)["gexy_received_at"]
        .max()
    )

    left = normalized.copy()
    left["symbol"] = left["symbol"].astype("string")
    left["vendor_trade_id"] = left["vendor_trade_id"].astype("string")
    merged = left.merge(
        receipt,
        on=["symbol", "vendor_trade_id"],
        how="left",
        validate="many_to_one",
    )
    if merged["gexy_received_at"].isna().any():
        raise ValueError("one or more normalized live trades could not be matched to gexy_received_at")
    return enforce_live_receive_causality(merged)


def normalize_massive_live_capture(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize a GEXY-stamped Massive WebSocket capture with true receive causality."""
    normalized = normalize_massive_stock_trades(raw)
    return _attach_receive_time_by_trade_id(
        normalized,
        raw,
        raw_symbol_col="sym",
        raw_trade_id_col="i",
    )


def normalize_alpaca_sip_live_capture(
    raw: pd.DataFrame,
    *,
    off_exchange_codes: Collection[str],
) -> pd.DataFrame:
    """Normalize a GEXY-stamped Alpaca SIP capture with true receive causality."""
    normalized = normalize_alpaca_sip_trades(raw, off_exchange_codes=off_exchange_codes)
    return _attach_receive_time_by_trade_id(
        normalized,
        raw,
        raw_symbol_col="S",
        raw_trade_id_col="i",
    )
