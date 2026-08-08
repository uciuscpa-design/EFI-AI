from packages.core.config import Settings
from packages.core.models import Side
from apps.api.services import TradingService


def test_signal_and_paper_execution() -> None:
    service = TradingService(Settings())
    service.ingest_quote("AAPL", 100, 100.10)
    intent = service.generate_signal("AAPL", 2)
    assert intent is not None
    decision, execution = service.execute_paper(intent)
    assert decision.approved
    assert execution is not None
    assert execution.status == "filled"


def test_manual_order_is_blocked_by_risk() -> None:
    service = TradingService(Settings(max_position_notional=100))
    intent = service.manual_intent("AAPL", Side.BUY, 2, 100)
    decision, execution = service.execute_paper(intent)
    assert not decision.approved
    assert execution is None
