from packages.core.models import OrderIntent, Quote, Side


class StrategyEngine:
    """Deterministic baseline strategy used for paper trading and integration tests."""

    def signal(self, quote: Quote, quantity: float = 1.0) -> OrderIntent | None:
        if quote.bid <= 0 or quote.ask <= 0 or quote.ask < quote.bid:
            return None
        return OrderIntent.now(quote.symbol, Side.BUY, quantity, quote.mid)
