from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import OptionExposure


class PositioningModel(str, Enum):
    STATIC = "static"
    FLOW_INFERRED = "flow_inferred"
    ENSEMBLE = "ensemble"


@dataclass(frozen=True)
class PositionEstimate:
    contract_id: str
    dealer_sign: float
    confidence: float
    model: PositioningModel
    rationale: str


def estimate_dealer_sign(option: OptionExposure, *, model: PositioningModel = PositioningModel.STATIC) -> PositionEstimate:
    """Return an explicit *inferred* dealer sign; never imply inventory is observed.

    STATIC treats the supplied contract sign as the dealer-side assumption. The
    flow-inferred and ensemble modes are reserved for adapters that supply trade
    direction/position evidence; until then they conservatively fall back to the
    supplied sign with lower confidence.
    """
    sign = 1.0 if option.position_sign >= 0 else -1.0
    if model is PositioningModel.STATIC:
        confidence = 0.50
        rationale = "Assumed from configured position sign; dealer inventory is unobserved."
    else:
        confidence = 0.20
        rationale = "No trade-direction evidence supplied; fallback to configured sign."
    return PositionEstimate(option.contract_id, sign, confidence, model, rationale)
