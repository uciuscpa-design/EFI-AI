from collections.abc import Mapping
from datetime import datetime, timezone

from packages.core.models import Quote


class MarketData:
    """Minimal market-data boundary; replace implementation with a live feed later."""

    def __init__(self, quotes: Mapping[str, Quote] | None = None) -> None:
        self._quotes = dict(quotes or {})

    def set_quote(self, symbol: str, bid: float, ask: float) -> Quote:
        quote = Quote(symbol.upper(), bid, ask, datetime.now(timezone.utc))
        self._quotes[quote.symbol] = quote
        return quote

    def quote(self, symbol: str) -> Quote | None:
        return self._quotes.get(symbol.upper())
