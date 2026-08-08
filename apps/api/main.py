import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from apps.api.middleware import request_logging_middleware
from apps.api.schemas import OrderRequest, QuoteRequest, SignalRequest
from apps.api.services import TradingService
from packages.core.audit import AuditLog
from packages.core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)
app = FastAPI(title=settings.app_name, version="0.3.0")
app.middleware("http")(request_logging_middleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
trading = TradingService(settings)
audit = AuditLog()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, object]:
    return {"status": "ready", "paper_trading": settings.paper_trading}


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "environment": settings.environment}


@app.post("/v1/market/quote")
def ingest_quote(request: QuoteRequest) -> dict[str, object]:
    quote = trading.ingest_quote(request.symbol, request.bid, request.ask)
    audit.record("quote_ingested", {"symbol": quote.symbol, "mid": quote.mid})
    return {"symbol": quote.symbol, "bid": quote.bid, "ask": quote.ask, "mid": quote.mid}


@app.post("/v1/strategy/signal")
def signal(request: SignalRequest) -> dict[str, object]:
    trading.ingest_quote(request.symbol, request.bid, request.ask)
    intent = trading.generate_signal(request.symbol, request.quantity)
    if intent is None:
        raise HTTPException(status_code=422, detail="Unable to generate signal")
    audit.record("signal_generated", {"symbol": intent.symbol, "side": intent.side, "quantity": intent.quantity})
    return intent.__dict__


@app.post("/v1/orders/paper")
def paper_order(request: OrderRequest) -> dict[str, object]:
    intent = trading.manual_intent(request.symbol, request.side, request.quantity, request.reference_price)
    decision, execution = trading.execute_paper(intent, request.daily_pnl)
    audit.record("paper_order_evaluated", {"symbol": intent.symbol, "approved": decision.approved, "reason": decision.reason})
    if execution is None:
        raise HTTPException(status_code=409, detail={"risk": decision.reason})
    return {"risk": decision.reason, "execution": execution.__dict__}


@app.get("/v1/audit/recent")
def recent_audit(limit: int = 100) -> list[dict[str, object]]:
    limit = max(1, min(limit, 500))
    return [event.__dict__ for event in audit.recent(limit)]
