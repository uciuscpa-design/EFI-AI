import json
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from packages.options.models import OptionContract, OptionGreeks, OptionSnapshot, OptionStyle, OptionType


class AlpacaOptionsError(RuntimeError):
    pass


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _as_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def contract_from_payload(payload: dict[str, Any]) -> OptionContract:
    multiplier = _as_float(payload.get("size"))
    if multiplier is None:
        raise ValueError("option contract is missing size/multiplier")
    expiration = _as_date(payload.get("expiration_date"))
    if expiration is None:
        raise ValueError("option contract is missing expiration_date")
    return OptionContract(
        symbol=str(payload["symbol"]),
        underlying_symbol=str(payload["underlying_symbol"]),
        root_symbol=str(payload.get("root_symbol") or payload["underlying_symbol"]),
        expiration_date=expiration,
        strike_price=float(payload["strike_price"]),
        option_type=OptionType(str(payload["type"])),
        style=OptionStyle(str(payload["style"])),
        multiplier=multiplier,
        open_interest=_as_float(payload.get("open_interest")),
        open_interest_date=_as_date(payload.get("open_interest_date")),
    )


def snapshot_from_payload(symbol: str, payload: dict[str, Any]) -> OptionSnapshot:
    quote = _first(payload, "latestQuote", "latest_quote") or {}
    trade = _first(payload, "latestTrade", "latest_trade") or {}
    greek_payload = payload.get("greeks") or None
    greeks = None
    if greek_payload is not None:
        greeks = OptionGreeks(
            delta=_as_float(greek_payload.get("delta")),
            gamma=_as_float(greek_payload.get("gamma")),
            theta=_as_float(greek_payload.get("theta")),
            vega=_as_float(greek_payload.get("vega")),
            rho=_as_float(greek_payload.get("rho")),
        )

    return OptionSnapshot(
        symbol=symbol,
        bid=_as_float(_first(quote, "bp", "bid_price")),
        ask=_as_float(_first(quote, "ap", "ask_price")),
        last=_as_float(_first(trade, "p", "price")),
        quote_timestamp=_as_datetime(_first(quote, "t", "timestamp")),
        trade_timestamp=_as_datetime(_first(trade, "t", "timestamp")),
        implied_volatility=_as_float(_first(payload, "impliedVolatility", "implied_volatility")),
        greeks=greeks,
    )


class AlpacaOptionsClient:
    """Small REST adapter for Alpaca option contracts and market snapshots.

    The adapter intentionally returns gexy domain objects and never logs API
    credentials. The default feed is indicative so development does not require
    an OPRA subscription.
    """

    def __init__(
        self,
        *,
        api_key_id: str,
        api_secret_key: str,
        feed: str = "indicative",
        trading_base_url: str = "https://paper-api.alpaca.markets",
        data_base_url: str = "https://data.alpaca.markets",
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_key_id or not api_secret_key:
            raise ValueError("Alpaca API credentials are required")
        if feed not in {"indicative", "opra"}:
            raise ValueError("feed must be 'indicative' or 'opra'")
        self.api_key_id = api_key_id
        self.api_secret_key = api_secret_key
        self.feed = feed
        self.trading_base_url = trading_base_url.rstrip("/")
        self.data_base_url = data_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_params = {key: value for key, value in (params or {}).items() if value is not None}
        if clean_params:
            url = f"{url}?{urlencode(clean_params)}"
        request = Request(
            url,
            headers={
                "APCA-API-KEY-ID": self.api_key_id,
                "APCA-API-SECRET-KEY": self.api_secret_key,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise AlpacaOptionsError(f"Alpaca HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise AlpacaOptionsError(f"Alpaca connection failed: {exc.reason}") from exc

    def contracts(
        self,
        *,
        underlying_symbols: Sequence[str],
        expiration_date: date | None = None,
        expiration_date_gte: date | None = None,
        expiration_date_lte: date | None = None,
        strike_price_gte: float | None = None,
        strike_price_lte: float | None = None,
        option_type: OptionType | None = None,
        root_symbol: str | None = None,
        max_records: int = 10_000,
    ) -> list[OptionContract]:
        if not underlying_symbols:
            raise ValueError("underlying_symbols cannot be empty")
        if max_records <= 0:
            raise ValueError("max_records must be positive")

        results: list[OptionContract] = []
        page_token: str | None = None
        while len(results) < max_records:
            page_size = min(10_000, max_records - len(results))
            payload = self._get_json(
                f"{self.trading_base_url}/v2/options/contracts",
                {
                    "underlying_symbols": ",".join(symbol.upper() for symbol in underlying_symbols),
                    "status": "active",
                    "expiration_date": expiration_date.isoformat() if expiration_date else None,
                    "expiration_date_gte": expiration_date_gte.isoformat() if expiration_date_gte else None,
                    "expiration_date_lte": expiration_date_lte.isoformat() if expiration_date_lte else None,
                    "strike_price_gte": strike_price_gte,
                    "strike_price_lte": strike_price_lte,
                    "type": option_type.value if option_type else None,
                    "root_symbol": root_symbol,
                    "limit": page_size,
                    "page_token": page_token,
                },
            )
            rows = payload.get("option_contracts") or payload.get("contracts") or []
            results.extend(contract_from_payload(row) for row in rows)
            page_token = payload.get("next_page_token")
            if not page_token or not rows:
                break
        return results[:max_records]

    def snapshots(self, symbols: Iterable[str]) -> dict[str, OptionSnapshot]:
        unique_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        results: dict[str, OptionSnapshot] = {}
        for offset in range(0, len(unique_symbols), 100):
            batch = unique_symbols[offset : offset + 100]
            if not batch:
                continue
            payload = self._get_json(
                f"{self.data_base_url}/v1beta1/options/snapshots",
                {"symbols": ",".join(batch), "feed": self.feed, "limit": len(batch)},
            )
            rows = payload.get("snapshots") or {}
            for symbol, row in rows.items():
                results[symbol] = snapshot_from_payload(symbol, row)
        return results
