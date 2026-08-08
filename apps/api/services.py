from packages.core.config import Settings
from packages.core.models import OrderIntent, Quote, Side
from packages.data.broker import Execution, PaperBroker
from packages.data.market import MarketData
from packages.risk.engine import RiskDecision, RiskEngine
from packages.strategy.engine import StrategyEngine


class TradingService:
    def __init__(self, settings: Settings) -> None:
        self.market = MarketData()
        self.strategy = StrategyEngine()
        self.risk = RiskEngine(settings.max_position_notional, settings.max_daily_loss)
        self.broker = PaperBroker()

    def ingest_quote(self, symbol: str, bid: float, ask: float) -> Quote:
        return self.market.set_quote(symbol, bid, ask)

    def generate_signal(self, symbol: str, quantity: float) -> OrderIntent | None:
        quote = self.market.quote(symbol)
        return self.strategy.signal(quote, quantity) if quote else None

    def evaluate(self, intent: OrderIntent, daily_pnl: float = 0.0) -> RiskDecision:
        return self.risk.evaluate(intent, daily_pnl)

    def execute_paper(self, intent: OrderIntent, daily_pnl: float = 0.0) -> tuple[RiskDecision, Execution | None]:
        decision = self.evaluate(intent, daily_pnl)
        if not decision.approved:
            return decision, None
        return decision, self.broker.submit(intent)

    def manual_intent(self, symbol: str, side: Side, quantity: float, reference_price: float) -> OrderIntent:
        return OrderIntent.now(symbol, side, quantity, reference_price)
