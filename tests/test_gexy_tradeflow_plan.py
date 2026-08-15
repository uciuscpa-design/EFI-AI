from __future__ import annotations

from datetime import date, time

import pandas as pd
import pytest

from scripts.gexy_tradeflow_plan import (
    DATASET,
    _chain_symbols,
    _estimate_schema_cost,
    _filter_chain_by_strike_band,
    _market_window,
    _parse_windows,
)


class _FakeMetadata:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_cost(self, **kwargs: object) -> float:
        self.calls.append(kwargs)
        return 0.123456


class _FakeClient:
    def __init__(self) -> None:
        self.metadata = _FakeMetadata()


def test_chain_symbols_are_exact_unique_sorted_raw_symbols() -> None:
    chain = pd.DataFrame(
        {
            "raw_symbol": [" SPXW  X ", "SPXW  A ", None, "SPXW  X ", ""],
        }
    )

    assert _chain_symbols(chain) == ["SPXW  A", "SPXW  X"]


def test_market_window_is_regular_spxw_session_in_new_york() -> None:
    start, end = _market_window(date(2026, 8, 13))

    assert start.isoformat() == "2026-08-13T09:30:00-04:00"
    assert end.isoformat() == "2026-08-13T16:00:00-04:00"


def test_parse_windows_keeps_sorted_nonoverlapping_ranges() -> None:
    windows = _parse_windows("15:30-16:00,09:30-10:00,12:30-13:00")

    assert windows == (
        (time(9, 30), time(10, 0)),
        (time(12, 30), time(13, 0)),
        (time(15, 30), time(16, 0)),
    )


def test_parse_windows_rejects_overlap() -> None:
    with pytest.raises(Exception):
        _parse_windows("09:30-10:00,09:45-10:15")


def test_strike_band_is_symmetric_and_inclusive() -> None:
    chain = pd.DataFrame(
        {
            "strike_price": [7549.0, 7550.0, 7750.0, 7950.0, 7951.0],
            "raw_symbol": ["a", "b", "c", "d", "e"],
        }
    )

    selected = _filter_chain_by_strike_band(chain, anchor=7750.0, band_points=200.0)

    assert selected["raw_symbol"].tolist() == ["b", "c", "d"]


def test_tcbbo_cost_estimate_uses_metadata_only_exact_symbols() -> None:
    client = _FakeClient()
    symbols = ["SPXW  260813C07750000", "SPXW  260813P07750000"]

    cost = _estimate_schema_cost(client, date(2026, 8, 13), symbols, "tcbbo")

    assert cost == 0.123456
    assert client.metadata.calls == [
        {
            "dataset": DATASET,
            "schema": "tcbbo",
            "stype_in": "raw_symbol",
            "symbols": symbols,
            "start": "2026-08-13T09:30:00-04:00",
            "end": "2026-08-13T16:00:00-04:00",
        }
    ]


def test_tcbbo_cost_estimate_respects_explicit_window() -> None:
    client = _FakeClient()
    symbols = ["SPXW  260813C07750000"]

    cost = _estimate_schema_cost(
        client,
        date(2026, 8, 13),
        symbols,
        "tcbbo",
        window=(time(15, 30), time(16, 0)),
    )

    assert cost == 0.123456
    assert client.metadata.calls[0]["start"] == "2026-08-13T15:30:00-04:00"
    assert client.metadata.calls[0]["end"] == "2026-08-13T16:00:00-04:00"
