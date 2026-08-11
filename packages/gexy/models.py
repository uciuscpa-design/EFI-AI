from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class GexyScenario(str, Enum):
    DEALER_LONG_GAMMA = "dealer_long_gamma"
    DEALER_SHORT_GAMMA = "dealer_short_gamma"
    MIXED = "mixed"


class GexyOption(BaseModel):
    symbol: str
    strike: float = Field(gt=0)
    option_type: str = Field(pattern="^(call|put)$")
    expiration: str
    open_interest: float = Field(ge=0)
    iv: float | None = Field(default=None, gt=0, lt=10)
    mid: float | None = Field(default=None, ge=0)
    bid: float | None = Field(default=None, ge=0)
    ask: float | None = Field(default=None, ge=0)
    days_to_expiry: float | None = Field(default=None, ge=0)
    multiplier: float = Field(default=100, gt=0)
    oi_confidence: float = Field(default=1.0, ge=0, le=1)


class GexyPoint(BaseModel):
    spot: float
    net_gex: float
    hedge_pressure_per_1pct: float
    call_gex: float
    put_gex: float


class GexySurface(BaseModel):
    reference_price: float
    scenario: GexyScenario
    points: list[GexyPoint]
    gamma_flip: float | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    data_quality: float = Field(ge=0, le=1)
    prediction_available: bool = False
    reason: str | None = None
