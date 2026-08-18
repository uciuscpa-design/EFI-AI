from __future__ import annotations

import pandas as pd

from packages.gexy.off_exchange_live_normalization import (
    normalize_alpaca_sip_live_capture,
    normalize_massive_live_capture,
)
from packages.gexy.off_exchange_streaming import (
    alpaca_trade_subscription,
    decode_websocket_payload,
    massive_trade_subscription,
    stamp_raw_stream_records,
)


def test_stream_subscription_builders_are_push_trade_only() -> None:
    massive = massive_trade_subscription(["SPY", "AAPL", "SPY"])
    alpaca = alpaca_trade_subscription(["SPY", "AAPL", "SPY"])

    assert massive == {"action": "subscribe", "params": "T.AAPL,T.SPY"}
    assert alpaca == {"action": "subscribe", "trades": ["AAPL", "SPY"]}
    assert "poll" not in str(massive).lower()
    assert "poll" not in str(alpaca).lower()


def test_decode_and_stamp_raw_stream_payload() -> None:
    records = decode_websocket_payload('[{"ev":"T","sym":"SPY","p":650.0}]')
    stamped = stamp_raw_stream_records(
        records,
        provider="massive",
        received_at="2026-08-17T13:30:01.500Z",
    )

    assert stamped[0]["gexy_provider"] == "massive"
    assert stamped[0]["gexy_received_at"] == "2026-08-17T13:30:01.500000Z"
    assert stamped[0]["p"] == 650.0


def test_massive_live_available_at_cannot_precede_client_receive() -> None:
    source_time = pd.Timestamp("2026-08-17T13:30:01.000Z")
    raw = pd.DataFrame(
        {
            "ev": ["T"],
            "sym": ["SPY"],
            "x": [4],
            "p": [650.0],
            "s": [1000],
            "t": [source_time.value // 1_000_000],
            "trfi": [201],
            "i": ["trade-1"],
            "gexy_received_at": ["2026-08-17T13:30:01.350Z"],
        }
    )
    normalized = normalize_massive_live_capture(raw)

    assert normalized.loc[0, "source_available_at"] == source_time
    assert normalized.loc[0, "gexy_received_at"] == pd.Timestamp("2026-08-17T13:30:01.350Z")
    assert normalized.loc[0, "available_at"] == pd.Timestamp("2026-08-17T13:30:01.350Z")
    assert normalized.loc[0, "available_at_basis"] == "max_provider_and_gexy_receive"


def test_alpaca_live_available_at_cannot_precede_client_receive() -> None:
    raw = pd.DataFrame(
        {
            "T": ["t"],
            "S": ["SPY"],
            "x": ["D"],
            "p": [650.0],
            "s": [500],
            "t": ["2026-08-17T13:30:01.000Z"],
            "i": [123],
            "z": ["A"],
            "gexy_received_at": ["2026-08-17T13:30:01.200Z"],
        }
    )
    normalized = normalize_alpaca_sip_live_capture(raw, off_exchange_codes={"D"})

    assert normalized.loc[0, "source_available_at"] == pd.Timestamp("2026-08-17T13:30:01.000Z")
    assert normalized.loc[0, "available_at"] == pd.Timestamp("2026-08-17T13:30:01.200Z")
    assert normalized.loc[0, "reporting_venue"] == "ALPACA_SIP_D"
