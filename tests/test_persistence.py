from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from packages.core.models import OrderIntent, Quote, Side
from packages.persistence.models import Base
from packages.persistence.service import PersistentService


def test_persistence_round_trip() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = PersistentService(session)
        quote = Quote("AAPL", 100, 100.10, datetime.now(timezone.utc))
        intent = OrderIntent.now("AAPL", Side.BUY, 1, 100.05)
        service.quote(quote)
        service.order(intent, "filled")
        event = service.audit("test_event", {"ok": True})
        assert event.event_type == "test_event"
        assert session.query(Base.metadata.tables["quotes"]).count() == 1
        assert session.query(Base.metadata.tables["orders"]).count() == 1
