from pydantic import BaseModel, Field

from packages.core.models import Side


class QuoteRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)


class SignalRequest(QuoteRequest):
    quantity: float = Field(default=1.0, gt=0)


class OrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: Side
    quantity: float = Field(gt=0)
    reference_price: float = Field(gt=0)
    daily_pnl: float = 0.0
