from fastapi import FastAPI, HTTPException

from apps.api.schemas import OrderRequest, QuoteRequest, SignalRequest
from apps.api.services import TradingService
from packages.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")
trading = TradingService(settings)


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
    return {"symbol": quote.symbol, "bid": quote.bid, "ask": quote.ask, "mid": quote.mid}


@app.post("/v1/strategy/signal")
def signal(request: SignalRequest) -> dict[str, object]:
    trading.ingest_quote(request.symbol, request.bid, request.ask)
    intent = trading.generate_signal(request.symbol, request.quantity)
    if intent is None:
        raise HTTPException(status_code=422, detail="Unable to generate signal")
    return intent.__dict__


@app.post("/v1/orders/paper")
def paper_order(request: OrderRequest) -> dict[str, object]:
    intent = trading.manual_intent(request.symbol, request.side, request.quantity, request.reference_price)
    decision, execution = trading.execute_paper(intent, request.daily_pnl)
    if execution is None:
        raise HTTPException(status_code=409, detail={"risk": decision.reason})
    return {"risk": decision.reason, "execution": execution.__dict__}
