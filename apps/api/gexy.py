from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.dependencies import require_api_key
from packages.gexy.engine import GexyEngine
from packages.gexy.models import GexyOption, GexyScenario

router = APIRouter(prefix="/v1/gexy", tags=["GEXY"], dependencies=[Depends(require_api_key)])


class GexySurfaceRequest(BaseModel):
    reference_price: float = Field(gt=0)
    scenario: GexyScenario = GexyScenario.DEALER_SHORT_GAMMA
    pct_range: float = Field(default=0.02, gt=0, le=0.20)
    steps: int = Field(default=81, ge=3, le=401)
    risk_free_rate: float = Field(default=0.0, ge=-0.10, le=1.0)
    options: list[GexyOption] = Field(min_length=1, max_length=5000)


@router.post("/surface")
def calculate_surface(request: GexySurfaceRequest):
    engine = GexyEngine(risk_free_rate=request.risk_free_rate)
    return engine.surface(
        request.options,
        reference_price=request.reference_price,
        scenario=request.scenario,
        pct_range=request.pct_range,
        steps=request.steps,
    )
