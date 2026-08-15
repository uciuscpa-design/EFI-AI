from __future__ import annotations

from datetime import date

import pandas as pd

from scripts.gexy_tradeflow_plan import DATASET, _chain_symbols, _estimate_schema_cost, _market_window


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
