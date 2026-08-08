import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from apps.api.dependencies import require_api_key
from apps.api.middleware import request_logging_middleware
from apps.api.schemas import OrderRequest, QuoteRequest, SignalRequest
from apps.api.services import TradingService
from packages.core.config import get_settings
from packages.persistence.db import SessionLocal, engine
from packages.persistence.models import AuditEventModel, Base
from packages.persistence.service import PersistentService

settings = get_settings()
logging.basicConfig(level=settings.log_level)
app = FastAPI(title=settings.app_name, version="0.5.1")
app.middleware("http")(request_logging_middleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
trading = TradingService(settings)


@app.on_event("startup")
def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "paper_trading": settings.paper_trading, "database": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "environment": settings.environment}


@app.post("/v1/market/quote", dependencies=[Depends(require_api_key)])
def ingest_quote(request: QuoteRequest) -> dict[str, object]:
    quote = trading.ingest_quote(request.symbol, request.bid, request.ask)
    with SessionLocal() as session:
        persistence = PersistentService(session)
        persistence.quote(quote)
        persistence.audit("quote_ingested", {"symbol": quote.symbol, "mid": quote.mid})
    return {"symbol": quote.symbol, "bid": quote.bid, "ask": quote.ask, "mid": quote.mid}


@app.post("/v1/strategy/signal", dependencies=[Depends(require_api_key)])
def signal(request: SignalRequest) -> dict[str, object]:
    trading.ingest_quote(request.symbol, request.bid, request.ask)
    intent = trading.generate_signal(request.symbol, request.quantity)
    if intent is None:
        raise HTTPException(status_code=422, detail="Unable to generate signal")
    with SessionLocal() as session:
        PersistentService(session).audit("signal_generated", {"symbol": intent.symbol, "side": intent.side.value, "quantity": intent.quantity})
    return {"symbol": intent.symbol, "side": intent.side.value, "quantity": intent.quantity, "reference_price": intent.reference_price, "created_at": intent.created_at}


@app.post("/v1/orders/paper", dependencies=[Depends(require_api_key)])
def paper_order(request: OrderRequest) -> dict[str, object]:
    intent = trading.manual_intent(request.symbol, request.side, request.quantity, request.reference_price)
    decision, execution = trading.execute_paper(intent, request.daily_pnl)
    with SessionLocal() as session:
        persistence = PersistentService(session)
        persistence.order(intent, "filled" if execution else "rejected")
        persistence.audit("paper_order_evaluated", {"symbol": intent.symbol, "approved": decision.approved, "reason": decision.reason})
    if execution is None:
        raise HTTPException(status_code=409, detail={"risk": decision.reason})
    return {"risk": decision.reason, "execution": {"order_id": execution.order_id, "status": execution.status}}


@app.get("/v1/audit/recent", dependencies=[Depends(require_api_key)])
def recent_audit(limit: int = 100) -> list[dict[str, object]]:
    limit = max(1, min(limit, 500))
    with SessionLocal() as session:
        rows = session.query(AuditEventModel).order_by(AuditEventModel.created_at.desc()).limit(limit).all()
    return [{"id": row.id, "event_type": row.event_type, "actor": row.actor, "payload": row.payload, "created_at": row.created_at} for row in rows]
