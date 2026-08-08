import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from packages.persistence.models import AuditEventModel, OrderModel, QuoteModel


class PersistenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_quote(self, symbol: str, bid: float, ask: float) -> QuoteModel:
        row = QuoteModel(symbol=symbol.upper(), bid=bid, ask=ask, created_at=datetime.now(timezone.utc))
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def save_order(self, symbol: str, side: str, quantity: float, reference_price: float, status: str) -> OrderModel:
        row = OrderModel(symbol=symbol.upper(), side=side, quantity=quantity, reference_price=reference_price, status=status, created_at=datetime.now(timezone.utc))
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def save_audit(self, event_type: str, actor: str, payload: dict) -> AuditEventModel:
        row = AuditEventModel(event_type=event_type, actor=actor, payload=json.dumps(payload, default=str), created_at=datetime.now(timezone.utc))
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row
