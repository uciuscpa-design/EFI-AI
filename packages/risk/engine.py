from dataclasses import dataclass

from packages.core.models import OrderIntent


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str


class RiskEngine:
    def __init__(self, max_position_notional: float = 10_000.0, max_daily_loss: float = 1_000.0) -> None:
        self.max_position_notional = max_position_notional
        self.max_daily_loss = max_daily_loss

    def evaluate(self, intent: OrderIntent, daily_pnl: float = 0.0) -> RiskDecision:
        notional = abs(intent.quantity * intent.reference_price)
        if notional > self.max_position_notional:
            return RiskDecision(False, "position_notional_limit")
        if daily_pnl <= -abs(self.max_daily_loss):
            return RiskDecision(False, "daily_loss_limit")
        return RiskDecision(True, "approved")
