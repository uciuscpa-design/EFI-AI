from packages.core.models import OrderIntent, Side
from packages.risk.engine import RiskEngine


def test_risk_approves_small_order() -> None:
    intent = OrderIntent.now("AAPL", Side.BUY, 2, 100)
    assert RiskEngine().evaluate(intent).approved


def test_risk_rejects_large_notional() -> None:
    intent = OrderIntent.now("AAPL", Side.BUY, 101, 100)
    decision = RiskEngine(max_position_notional=10_000).evaluate(intent)
    assert not decision.approved
    assert decision.reason == "position_notional_limit"


def test_risk_rejects_daily_loss_limit() -> None:
    intent = OrderIntent.now("AAPL", Side.BUY, 1, 100)
    decision = RiskEngine(max_daily_loss=1_000).evaluate(intent, daily_pnl=-1_000)
    assert not decision.approved
    assert decision.reason == "daily_loss_limit"
