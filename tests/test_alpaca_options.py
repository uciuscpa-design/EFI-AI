from __future__ import annotations

import httpx
import pytest

from packages.core.config import Settings
from packages.data.alpaca_options import (
    AlpacaOptionsClient,
    AlpacaOptionsError,
    option_chain_snapshot_count,
)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APCA_API_KEY_ID": "test-key",
        "APCA_API_SECRET_KEY": "test-secret",
        "APCA_DATA_BASE_URL": "https://data.alpaca.markets",
        "APCA_API_BASE_URL": "https://paper-api.alpaca.markets",
        "APCA_OPTIONS_FEED": "indicative",
    }
    values.update(overrides)
    return Settings(**values)


def test_missing_credentials_fail_before_request() -> None:
    settings = Settings(APCA_API_KEY_ID="", APCA_API_SECRET_KEY="")
    client = AlpacaOptionsClient(settings=settings, client=httpx.Client())

    with pytest.raises(AlpacaOptionsError, match="credentials are missing"):
        client.fetch_option_chain("SPX")


def test_auth_probe_sends_alpaca_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta1/options/meta/exchanges"
        assert request.headers["APCA-API-KEY-ID"] == "test-key"
        assert request.headers["APCA-API-SECRET-KEY"] == "test-secret"
        return httpx.Response(200, json={"C": "Cboe Options"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AlpacaOptionsClient(settings=_settings(), client=http_client)
        payload = client.check_authentication()

    assert payload == {"C": "Cboe Options"}


def test_option_contracts_fetches_oi_metadata_from_trading_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "paper-api.alpaca.markets"
        assert request.url.path == "/v2/options/contracts"
        assert request.url.params["underlying_symbols"] == "SPX"
        assert request.url.params["expiration_date"] == "2026-08-14"
        assert request.url.params["strike_price_gte"] == "7790.0"
        assert request.url.params["strike_price_lte"] == "7810.0"
        assert request.url.params["limit"] == "50"
        return httpx.Response(
            200,
            json={
                "option_contracts": [
                    {
                        "symbol": "SPXW260814C07800000",
                        "open_interest": "6186",
                        "size": "100",
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AlpacaOptionsClient(settings=_settings(), client=http_client)
        payload = client.fetch_option_contracts(
            "spx",
            expiration_date="2026-08-14",
            strike_price_gte=7790,
            strike_price_lte=7810,
            limit=50,
        )

    assert payload["option_contracts"][0]["open_interest"] == "6186"


def test_explicit_snapshots_fetch_supports_multiple_contracts() -> None:
    symbols = ["SPXW260814C07800000", "SPXW260814P07800000"]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta1/options/snapshots"
        assert request.url.params["symbols"] == ",".join(symbols)
        assert request.url.params["feed"] == "indicative"
        return httpx.Response(200, json={"snapshots": {symbol: {} for symbol in symbols}})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AlpacaOptionsClient(settings=_settings(), client=http_client)
        payload = client.fetch_option_snapshots(symbols)

    assert len(payload["snapshots"]) == 2


def test_option_chain_success_and_count() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta1/options/snapshots/SPX"
        assert request.url.params["feed"] == "indicative"
        assert request.url.params["limit"] == "25"
        return httpx.Response(
            200,
            json={
                "snapshots": {
                    "SPXW260814C06000000": {"greeks": {"gamma": 0.001}},
                    "SPXW260814P06000000": {"greeks": {"gamma": 0.0011}},
                },
                "next_page_token": None,
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AlpacaOptionsClient(settings=_settings(), client=http_client)
        payload = client.fetch_option_chain("spx", limit=25)

    assert option_chain_snapshot_count(payload) == 2


def test_401_diagnostic_does_not_expose_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid credentials"})

    transport = httpx.MockTransport(handler)
    settings = _settings()
    with httpx.Client(transport=transport) as http_client:
        client = AlpacaOptionsClient(settings=settings, client=http_client)
        with pytest.raises(AlpacaOptionsError) as exc_info:
            client.fetch_option_chain("SPX")

    message = str(exc_info.value)
    assert "HTTP 401" in message
    assert "test-key" not in message
    assert "test-secret" not in message


def test_feed_and_limit_validation() -> None:
    client = AlpacaOptionsClient(settings=_settings(), client=httpx.Client())

    with pytest.raises(ValueError, match="feed must"):
        client.fetch_option_chain("SPX", feed="unknown")
    with pytest.raises(ValueError, match="limit must"):
        client.fetch_option_chain("SPX", limit=1001)
    with pytest.raises(ValueError, match="10000"):
        client.fetch_option_contracts("SPX", limit=10001)
    with pytest.raises(ValueError, match="between 1 and 100"):
        client.fetch_option_snapshots([])
