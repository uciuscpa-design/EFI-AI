from __future__ import annotations

from datetime import date

import pytest

from packages.gexy.greeks import black_scholes_greeks
from packages.gexy.levels import rank_levels_by_unsigned_gex, summarize_gex_walls
from packages.gexy.models import NormalizedOptionSurface, OptionSurfacePoint, OptionType
from packages.gexy.pipeline import build_enriched_gexy_surface


def _point(
    *,
    symbol: str,
    option_type: OptionType,
    strike: float,
    open_interest: float,
    gamma: float | None = None,
    delta: float | None = None,
    implied_volatility: float | None = None,
    bid: float | None = None,
    ask: float | None = None,
) -> OptionSurfacePoint:
    return OptionSurfacePoint(
        symbol=symbol,
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=option_type,
        strike=strike,
        multiplier=100.0,
        open_interest=open_interest,
        gamma=gamma,
        delta=delta,
        implied_volatility=implied_volatility,
        bid=bid,
        ask=ask,
    )


def test_wall_summary_extracts_ranked_landmarks() -> None:
    normalized = NormalizedOptionSurface(
        points=(
            _point(
                symbol="C7790",
                option_type=OptionType.CALL,
                strike=7790.0,
                open_interest=200.0,
                gamma=0.010,
                delta=0.55,
            ),
            _point(
                symbol="P7790",
                option_type=OptionType.PUT,
                strike=7790.0,
                open_interest=50.0,
                gamma=0.010,
                delta=-0.45,
            ),
            _point(
                symbol="P7810",
                option_type=OptionType.PUT,
                strike=7810.0,
                open_interest=300.0,
                gamma=0.012,
                delta=-0.55,
            ),
        ),
        contracts_seen=3,
        invalid_contracts=0,
        missing_snapshots=0,
    )

    result = build_enriched_gexy_surface(
        normalized,
        spot=7800.0,
        time_to_expiry_years={date(2026, 8, 21): 7 / 365},
    )
    walls = summarize_gex_walls(result.surface)
    ranking = rank_levels_by_unsigned_gex(result.surface)

    assert walls.strongest_unsigned is not None
    assert walls.strongest_unsigned.strike == 7810.0
    assert walls.strongest_positive_heuristic is not None
    assert walls.strongest_positive_heuristic.strike == 7790.0
    assert walls.strongest_negative_heuristic is not None
    assert walls.strongest_negative_heuristic.strike == 7810.0
    assert walls.nearest_below_spot is not None
    assert walls.nearest_below_spot.strike == 7790.0
    assert walls.nearest_above_spot is not None
    assert walls.nearest_above_spot.strike == 7810.0
    assert ranking[0].strike == 7810.0


def test_pipeline_enriches_alpaca_iv_and_quote_implied_iv() -> None:
    spot = 7800.0
    tte = 7 / 365
    put_price = black_scholes_greeks(
        option_type=OptionType.PUT,
        spot=spot,
        strike=7800.0,
        time_to_expiry_years=tte,
        volatility=0.23,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    ).price
    normalized = NormalizedOptionSurface(
        points=(
            _point(
                symbol="ALPACA_IV",
                option_type=OptionType.CALL,
                strike=7795.0,
                open_interest=100.0,
                implied_volatility=0.21,
            ),
            _point(
                symbol="QUOTE_IV",
                option_type=OptionType.PUT,
                strike=7800.0,
                open_interest=150.0,
                bid=put_price - 0.05,
                ask=put_price + 0.05,
            ),
            _point(
                symbol="NATIVE",
                option_type=OptionType.CALL,
                strike=7805.0,
                open_interest=80.0,
                gamma=0.008,
                delta=0.45,
            ),
        ),
        contracts_seen=3,
        invalid_contracts=0,
        missing_snapshots=0,
    )

    result = build_enriched_gexy_surface(
        normalized,
        spot=spot,
        time_to_expiry_years={date(2026, 8, 21): tte},
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )

    assert result.greek_sources.alpaca == 1
    assert result.greek_sources.alpaca_iv == 1
    assert result.greek_sources.quote_implied_iv == 1
    assert result.greek_sources.unavailable == 0
    assert result.surface.contracts_used == 3
    assert result.surface.contracts_missing_gamma == 0
    assert all(point.gamma is not None for point in result.points)


def test_pipeline_keeps_unenriched_contract_when_expiry_timing_missing() -> None:
    normalized = NormalizedOptionSurface(
        points=(
            _point(
                symbol="NO_TTE",
                option_type=OptionType.CALL,
                strike=7800.0,
                open_interest=100.0,
                implied_volatility=0.20,
            ),
        ),
        contracts_seen=1,
        invalid_contracts=0,
        missing_snapshots=0,
    )

    result = build_enriched_gexy_surface(
        normalized,
        spot=7800.0,
        time_to_expiry_years={},
    )

    assert result.greek_sources.unavailable == 1
    assert result.surface.contracts_seen == 1
    assert result.surface.contracts_used == 0
    assert result.surface.contracts_missing_gamma == 1
    assert result.points[0].gamma is None


def test_level_ranking_rejects_invalid_limit() -> None:
    normalized = NormalizedOptionSurface(
        points=(),
        contracts_seen=0,
        invalid_contracts=0,
        missing_snapshots=0,
    )
    result = build_enriched_gexy_surface(
        normalized,
        spot=7800.0,
        time_to_expiry_years={},
    )

    with pytest.raises(ValueError, match="at least 1"):
        rank_levels_by_unsigned_gex(result.surface, limit=0)
