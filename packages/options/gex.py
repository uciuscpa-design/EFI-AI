from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from packages.options.models import OptionContract, OptionType


class GexSignMethod(StrEnum):
    UNSIGNED = "unsigned"
    CALL_PUT_PROXY = "call_put_proxy"


@dataclass(frozen=True)
class GexContribution:
    symbol: str
    strike_price: float
    option_type: OptionType
    gamma: float
    open_interest: float
    multiplier: float
    exposure_per_1pct: float


@dataclass(frozen=True)
class GexSummary:
    spot: float
    sign_method: GexSignMethod
    net_exposure_per_1pct: float
    gross_exposure_per_1pct: float
    by_strike: dict[float, float]
    contributions: tuple[GexContribution, ...]
    skipped_symbols: tuple[str, ...]


def gamma_exposure_per_1pct(
    *,
    contract: OptionContract,
    gamma: float,
    spot: float,
    sign_method: GexSignMethod = GexSignMethod.CALL_PUT_PROXY,
) -> float:
    """Return gamma exposure for a 1% underlying move.

    CALL_PUT_PROXY applies +1 to calls and -1 to puts. It is a transparent
    heuristic only: open interest does not identify the dealer/customer side,
    so this value must not be described as observed dealer gamma positioning.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")
    if gamma < 0:
        raise ValueError("gamma cannot be negative")
    if contract.multiplier <= 0:
        raise ValueError("contract multiplier must be positive")
    if contract.open_interest is None or contract.open_interest < 0:
        raise ValueError("open_interest must be present and non-negative")

    sign = 1.0
    if sign_method is GexSignMethod.CALL_PUT_PROXY:
        sign = 1.0 if contract.option_type is OptionType.CALL else -1.0
    elif sign_method is not GexSignMethod.UNSIGNED:
        raise ValueError(f"unsupported sign_method: {sign_method}")

    return sign * gamma * contract.open_interest * contract.multiplier * spot * spot * 0.01


def aggregate_gex(
    records: Iterable[tuple[OptionContract, float | None]],
    *,
    spot: float,
    sign_method: GexSignMethod = GexSignMethod.CALL_PUT_PROXY,
) -> GexSummary:
    """Aggregate contract gamma/OI into strike and total GEX metrics."""
    contributions: list[GexContribution] = []
    skipped: list[str] = []
    by_strike: dict[float, float] = {}

    for contract, gamma in records:
        if gamma is None or contract.open_interest is None:
            skipped.append(contract.symbol)
            continue
        exposure = gamma_exposure_per_1pct(
            contract=contract,
            gamma=gamma,
            spot=spot,
            sign_method=sign_method,
        )
        contribution = GexContribution(
            symbol=contract.symbol,
            strike_price=contract.strike_price,
            option_type=contract.option_type,
            gamma=gamma,
            open_interest=contract.open_interest,
            multiplier=contract.multiplier,
            exposure_per_1pct=exposure,
        )
        contributions.append(contribution)
        by_strike[contract.strike_price] = by_strike.get(contract.strike_price, 0.0) + exposure

    net = sum(item.exposure_per_1pct for item in contributions)
    gross = sum(abs(item.exposure_per_1pct) for item in contributions)
    return GexSummary(
        spot=spot,
        sign_method=sign_method,
        net_exposure_per_1pct=net,
        gross_exposure_per_1pct=gross,
        by_strike=by_strike,
        contributions=tuple(contributions),
        skipped_symbols=tuple(skipped),
    )
