from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

import pandas as pd


MASSIVE_REALTIME_STOCKS_URL = "wss://socket.massive.com/stocks"
MASSIVE_DELAYED_STOCKS_URL = "wss://delayed.massive.com/stocks"
ALPACA_SIP_STOCKS_URL = "wss://stream.data.alpaca.markets/v2/sip"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def massive_auth_message(api_key: str) -> dict[str, str]:
    if not api_key:
        raise ValueError("Massive API key must not be empty")
    return {"action": "auth", "params": api_key}


def massive_trade_subscription(symbols: Iterable[str]) -> dict[str, str]:
    cleaned = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
    if not cleaned:
        raise ValueError("at least one Massive stock symbol is required")
    return {"action": "subscribe", "params": ",".join(f"T.{symbol}" for symbol in cleaned)}


def alpaca_auth_message(api_key: str, secret_key: str) -> dict[str, str]:
    if not api_key or not secret_key:
        raise ValueError("Alpaca API key and secret must not be empty")
    return {"action": "auth", "key": api_key, "secret": secret_key}


def alpaca_trade_subscription(symbols: Iterable[str]) -> dict[str, list[str] | str]:
    cleaned = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
    if not cleaned:
        raise ValueError("at least one Alpaca stock symbol is required")
    return {"action": "subscribe", "trades": cleaned}


def decode_websocket_payload(payload: str | bytes) -> list[dict[str, Any]]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    parsed = json.loads(payload)
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
        return parsed
    raise ValueError("WebSocket payload must be a JSON object or list of JSON objects")


def stamp_raw_stream_records(
    records: Iterable[Mapping[str, Any]],
    *,
    provider: str,
    received_at: str | pd.Timestamp | None = None,
) -> list[dict[str, Any]]:
    """Attach GEXY client receive time to immutable raw stream records.

    The source's own SIP/TRF/capture timestamps remain untouched. The client
    receive timestamp records when GEXY could actually observe the message and is
    required for latency-aware prospective research.
    """
    observed = pd.Timestamp(received_at if received_at is not None else utc_now_iso())
    if observed.tzinfo is None:
        raise ValueError("received_at must include an explicit timezone")
    observed = observed.tz_convert("UTC")
    observed_text = observed.isoformat().replace("+00:00", "Z")

    stamped: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        item["gexy_received_at"] = observed_text
        item["gexy_provider"] = provider
        stamped.append(item)
    return stamped


def enforce_live_receive_causality(
    normalized: pd.DataFrame,
    *,
    received_at_col: str = "gexy_received_at",
) -> pd.DataFrame:
    """Ensure normalized live records are not available before GEXY received them.

    Provider timestamps can precede local receipt by network/processing latency.
    For live research, ``available_at`` becomes the later of the provider-derived
    availability timestamp and the GEXY client receive timestamp. The original
    provider-derived value is preserved as ``source_available_at``.
    """
    required = {"available_at", received_at_col}
    missing = sorted(required.difference(normalized.columns))
    if missing:
        raise ValueError(f"live normalized frame missing columns: {', '.join(missing)}")

    frame = normalized.copy()
    source_time = pd.to_datetime(frame["available_at"], utc=True, errors="coerce")
    received_time = pd.to_datetime(frame[received_at_col], utc=True, errors="coerce")
    frame["source_available_at"] = source_time
    frame["gexy_received_at"] = received_time
    frame["available_at"] = pd.concat(
        [source_time.rename("source"), received_time.rename("received")],
        axis=1,
    ).max(axis=1)
    frame["available_at_basis"] = "max_provider_and_gexy_receive"
    return frame
