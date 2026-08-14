from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from packages.core.config import Settings, get_settings


class AlpacaOptionsError(RuntimeError):
    """Raised when Alpaca option data cannot be retrieved."""


class AlpacaOptionsClient:
    """Authenticated boundary around Alpaca option metadata and market-data APIs."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def __enter__(self) -> "AlpacaOptionsClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    @property
    def credentials_configured(self) -> bool:
        return self.settings.has_alpaca_credentials

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        if not self.credentials_configured:
            raise AlpacaOptionsError(
                "Alpaca credentials are missing. Set APCA_API_KEY_ID and "
                "APCA_API_SECRET_KEY in the project .env file."
            )
        return {
            "APCA-API-KEY-ID": self.settings.alpaca_api_key_id,
            "APCA-API-SECRET-KEY": self.settings.alpaca_api_secret_key,
        }

    def _feed(self, feed: str | None) -> str:
        selected_feed = (feed or self.settings.alpaca_options_feed).strip().lower()
        if selected_feed not in {"indicative", "opra"}:
            raise ValueError("feed must be 'indicative' or 'opra'")
        return selected_feed

    @staticmethod
    def _symbol(value: str) -> str:
        symbol = value.strip().upper()
        if not symbol:
            raise ValueError("symbol must not be empty")
        return symbol

    def check_authentication(self) -> dict[str, Any]:
        """Call a lightweight options metadata endpoint to validate auth headers."""
        url = f"{self.settings.alpaca_data_base_url.rstrip('/')}/v1beta1/options/meta/exchanges"
        return self._get_json(url)

    def fetch_option_contracts(
        self,
        underlying_symbol: str,
        *,
        expiration_date: str | None = None,
        expiration_date_gte: str | None = None,
        expiration_date_lte: str | None = None,
        strike_price_gte: float | None = None,
        strike_price_lte: float | None = None,
        contract_type: str | None = None,
        root_symbol: str | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Return option contract metadata, including OI and contract multiplier."""
        symbol = self._symbol(underlying_symbol)
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000")
        if contract_type is not None and contract_type not in {"call", "put"}:
            raise ValueError("contract_type must be 'call' or 'put'")

        params: dict[str, str | int | float] = {
            "underlying_symbols": symbol,
            "limit": limit,
        }
        optional: dict[str, str | float | None] = {
            "expiration_date": expiration_date,
            "expiration_date_gte": expiration_date_gte,
            "expiration_date_lte": expiration_date_lte,
            "strike_price_gte": strike_price_gte,
            "strike_price_lte": strike_price_lte,
            "type": contract_type,
            "root_symbol": root_symbol,
        }
        params.update({key: value for key, value in optional.items() if value is not None})

        url = f"{self.settings.alpaca_trading_base_url.rstrip('/')}/v2/options/contracts"
        return self._get_json(url, params=params)

    def fetch_option_snapshots(
        self,
        symbols: str | Iterable[str],
        *,
        feed: str | None = None,
    ) -> dict[str, Any]:
        """Return market snapshots for one to 100 explicit option contract symbols."""
        if isinstance(symbols, str):
            normalized = [self._symbol(symbols)]
        else:
            normalized = [self._symbol(symbol) for symbol in symbols]
        if not 1 <= len(normalized) <= 100:
            raise ValueError("symbols must contain between 1 and 100 contracts")

        url = f"{self.settings.alpaca_data_base_url.rstrip('/')}/v1beta1/options/snapshots"
        return self._get_json(
            url,
            params={
                "symbols": ",".join(normalized),
                "feed": self._feed(feed),
            },
        )

    def fetch_option_snapshots_batched(
        self,
        symbols: Iterable[str],
        *,
        feed: str | None = None,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """Fetch any number of explicit option snapshots in API-safe batches."""
        normalized = [self._symbol(symbol) for symbol in symbols]
        if not normalized:
            raise ValueError("symbols must contain at least one contract")
        if not 1 <= batch_size <= 100:
            raise ValueError("batch_size must be between 1 and 100")

        selected_feed = self._feed(feed)
        merged: dict[str, Any] = {}
        for start in range(0, len(normalized), batch_size):
            payload = self.fetch_option_snapshots(
                normalized[start : start + batch_size],
                feed=selected_feed,
            )
            snapshots = payload.get("snapshots")
            if isinstance(snapshots, dict):
                merged.update(snapshots)
        return {"snapshots": merged}

    def fetch_option_chain(
        self,
        underlying_symbol: str,
        *,
        limit: int = 100,
        feed: str | None = None,
        contract_type: str | None = None,
        strike_price_gte: float | None = None,
        strike_price_lte: float | None = None,
        expiration_date: str | None = None,
        expiration_date_gte: str | None = None,
        expiration_date_lte: str | None = None,
        root_symbol: str | None = None,
    ) -> dict[str, Any]:
        """Return Alpaca's latest option snapshots for an underlying symbol."""
        symbol = self._symbol(underlying_symbol)
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        if contract_type is not None and contract_type not in {"call", "put"}:
            raise ValueError("contract_type must be 'call' or 'put'")

        params: dict[str, str | int | float] = {
            "feed": self._feed(feed),
            "limit": limit,
        }
        optional: dict[str, str | float | None] = {
            "type": contract_type,
            "strike_price_gte": strike_price_gte,
            "strike_price_lte": strike_price_lte,
            "expiration_date": expiration_date,
            "expiration_date_gte": expiration_date_gte,
            "expiration_date_lte": expiration_date_lte,
            "root_symbol": root_symbol,
        }
        params.update({key: value for key, value in optional.items() if value is not None})

        url = (
            f"{self.settings.alpaca_data_base_url.rstrip('/')}"
            f"/v1beta1/options/snapshots/{symbol}"
        )
        return self._get_json(url, params=params)

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, str | int | float] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.get(url, headers=self._headers(), params=params)
        except httpx.HTTPError as exc:
            raise AlpacaOptionsError(f"Alpaca request failed before a response was received: {exc}") from exc

        if response.status_code == 401:
            raise AlpacaOptionsError(
                "Alpaca returned HTTP 401: authentication headers were rejected. "
                "Verify that APCA_API_KEY_ID and APCA_API_SECRET_KEY are the matching "
                "key pair and that the .env file is being loaded from the EFI-AI project root."
            )
        if response.status_code == 403:
            raise AlpacaOptionsError(
                "Alpaca returned HTTP 403: credentials were recognized but this "
                "resource or data feed is not permitted for the account."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text.strip().replace("\n", " ")[:500]
            raise AlpacaOptionsError(
                f"Alpaca returned HTTP {response.status_code}: {detail or 'no response body'}"
            ) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise AlpacaOptionsError("Alpaca returned an unexpected non-object JSON payload")
        return payload


def option_chain_snapshot_count(payload: dict[str, Any]) -> int:
    """Count option snapshots without assuming more than Alpaca's top-level shape."""
    snapshots = payload.get("snapshots")
    return len(snapshots) if isinstance(snapshots, dict) else 0
