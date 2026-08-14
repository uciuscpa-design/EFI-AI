from __future__ import annotations

from typing import Any

import httpx

from packages.core.config import Settings, get_settings


class AlpacaOptionsError(RuntimeError):
    """Raised when Alpaca option market data cannot be retrieved."""


class AlpacaOptionsClient:
    """Small authenticated boundary around Alpaca's option snapshot API."""

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

    def check_authentication(self) -> dict[str, Any]:
        """Call a lightweight options metadata endpoint to validate auth headers."""
        url = f"{self.settings.alpaca_data_base_url.rstrip('/')}/v1beta1/options/meta/exchanges"
        return self._get_json(url)

    def fetch_option_chain(
        self,
        underlying_symbol: str,
        *,
        limit: int = 100,
        feed: str | None = None,
    ) -> dict[str, Any]:
        """Return Alpaca's latest option snapshots for an underlying symbol."""
        symbol = underlying_symbol.strip().upper()
        if not symbol:
            raise ValueError("underlying_symbol must not be empty")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

        selected_feed = (feed or self.settings.alpaca_options_feed).strip().lower()
        if selected_feed not in {"indicative", "opra"}:
            raise ValueError("feed must be 'indicative' or 'opra'")

        url = (
            f"{self.settings.alpaca_data_base_url.rstrip('/')}"
            f"/v1beta1/options/snapshots/{symbol}"
        )
        return self._get_json(
            url,
            params={"feed": selected_feed, "limit": limit},
        )

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, str | int] | None = None,
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
                "Alpaca returned HTTP 403: credentials were recognized but this data "
                "resource/feed is not permitted for the account."
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
