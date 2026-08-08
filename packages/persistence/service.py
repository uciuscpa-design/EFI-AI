import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.core.models import OrderIntent, Quote
from packages.persistence.models import AuditEventModel, OrderModel, QuoteModel


class PersistentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def quote(self, quote: Quote) -> QuoteModel:
        row = QuoteModel(symbol=quote.symbol, bid=quote.bid, ask=quote.ask, created_at=quote.timestamp)
        self.session.add(row)
        self.session.commit()
        return row

    def order(self, intent: OrderIntent, status: str) -> OrderModel:
        row = OrderModel(symbol=intent.symbol, side=intent.side.value, quantity=intent.quantity, reference_price=intent.reference_price, status=status, created_at=intent.created_at)
        self.session.add(row)
        self.session.commit()
        return row

    def audit(self, event_type: str, payload: dict, actor: str = "system") -> AuditEventModel:
        row = AuditEventModel(event_type=event_type, actor=actor, payload=json.dumps(payload, default=str), created_at=datetime.now(timezone.utc))
        self.session.add(row)
        self.session.commit()
        return row
