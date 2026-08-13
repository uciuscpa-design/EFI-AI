from __future__ import annotations

from dataclasses import dataclass
from math import tanh


@dataclass(frozen=True)
class RegimeScore:
    score: float
    label: str


def regime_score(*, signed_gex: float, spot_change: float, confidence: float = 1.0) -> RegimeScore:
    """Map signed gamma feedback into a bounded market-regime score.

    Positive scores mean stabilizing/pinning feedback: hedge flow opposes the
    observed price move. Negative scores mean amplifying/breakout feedback:
    hedge flow reinforces the move. The score is bounded to [-1, 1].
    """
    if not -1.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between -1 and 1")
    if spot_change == 0 or signed_gex == 0 or confidence == 0:
        return RegimeScore(0.0, "neutral")

    # First-order hedge demand is proportional to -signed_gex * dS. Therefore
    # positive signed gamma is stabilizing and negative signed gamma amplifying.
    raw = signed_gex * abs(spot_change) * confidence
    scale = max(abs(signed_gex), 1.0) * max(abs(spot_change), 1.0)
    score = tanh(raw / scale)
    if score > 0.15:
        label = "stabilizing"
    elif score < -0.15:
        label = "amplifying"
    else:
        label = "neutral"
    return RegimeScore(score, label)
