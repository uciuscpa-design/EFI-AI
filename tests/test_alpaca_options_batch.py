from __future__ import annotations

import httpx
import pytest

from packages.core.config import Settings
from packages.data.alpaca_options import AlpacaOptionsClient


def _settings() -> Settings:
    return Settings(
        APCA_API_KEY_ID="test-key",
        APCA_API_SECRET_KEY="test-secret",
        APCA_DATA_BASE_URL="https://data.alpaca.markets",
        APCA_API_BASE_URL="https://paper-api.alpaca.markets",
        APCA_OPTIONS_FEED="indicative",
    )


def test_batched_snapshots_chunks_and_merges_results() -> None:
    symbols = [f"OPT{i:03d}" for i in range(205)]
    request_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested = request.url.params["symbols"].split(",")
        request_sizes.append(len(requested))
        assert request.url.params["feed"] == "indicative"
        return httpx.Response(
            200,
            json={"snapshots": {symbol: {"symbol": symbol} for symbol in requested}},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AlpacaOptionsClient(settings=_settings(), client=http_client)
        payload = client.fetch_option_snapshots_batched(symbols)

    assert request_sizes == [100, 100, 5]
    assert len(payload["snapshots"]) == 205
    assert payload["snapshots"]["OPT204"]["symbol"] == "OPT204"


def test_batched_snapshots_validates_inputs() -> None:
    client = AlpacaOptionsClient(settings=_settings(), client=httpx.Client())

    with pytest.raises(ValueError, match="at least one"):
        client.fetch_option_snapshots_batched([])
    with pytest.raises(ValueError, match="batch_size"):
        client.fetch_option_snapshots_batched(["SPXW260821C07800000"], batch_size=101)
