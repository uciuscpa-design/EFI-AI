from __future__ import annotations

from datetime import date

import pytest

from packages.gexy.exposure import build_gex_surface, contract_exposure
from packages.gexy.greeks import (
    black_scholes_greeks,
    enrich_missing_greeks,
    implied_volatility_from_price,
)
from packages.gexy.models import OptionSurfacePoint, OptionType
from packages.gexy.normalization import normalize_alpaca_option_surface


def test_normalizer_joins_contract_metadata_and_snapshot() -> None:
    contracts = {
        "option_contracts": [
            {
                "symbol": "SPXW260814C07800000",
                "underlying_symbol": "SPX",
                "expiration_date": "2026-08-14",
                "type": "call",
                "strike_price": "7800",
                "size": "100",
                "open_interest": "6186",
                "open_interest_date": "2026-08-12",
            }
        ]
    }
    snapshots = {
        "snapshots": {
            "SPXW260814C07800000": {
                "latest_quote": {
                    "bid_price": 14.1,
                    "ask_price": 14.4,
                    "bid_size": 10,
                    "ask_size": 12,
                    "timestamp": "2026-08-14T19:30:00+00:00",
                },
                "latest_trade": {
                    "price": 14.25,
                    "size": 2,
                    "timestamp": "2026-08-14T19:29:59+00:00",
                },
                "implied_volatility": 0.18,
                "greeks": {
                    "delta": 0.52,
                    "gamma": 0.01,
                    "theta": -1.2,
                    "vega": 0.5,
                    "rho": 0.01,
                },
            }
        }
    }

    surface = normalize_alpaca_option_surface(contracts, snapshots)

    assert surface.contracts_seen == 1
    assert surface.invalid_contracts == 0
    assert surface.missing_snapshots == 0
    point = surface.points[0]
    assert point.symbol == "SPXW260814C07800000"
    assert point.expiration_date == date(2026, 8, 14)
    assert point.option_type is OptionType.CALL
    assert point.strike == 7800.0
    assert point.multiplier == 100.0
    assert point.open_interest == 6186.0
    assert point.mid == pytest.approx(14.25)
    assert point.gamma == pytest.approx(0.01)


def test_normalizer_supports_compact_alpaca_snapshot_keys() -> None:
    contracts = {
        "option_contracts": [
            {
                "symbol": "SPXW260821P07800000",
                "underlying_symbol": "SPX",
                "expiration_date": "2026-08-21",
                "type": "put",
                "strike_price": "7800",
                "size": "100",
                "open_interest": "471",
            }
        ]
    }
    snapshots = {
        "snapshots": {
            "SPXW260821P07800000": {
                "latestQuote": {
                    "bp": 41.0,
                    "ap": 41.5,
                    "bs": 3,
                    "as": 4,
                    "t": "2026-08-14T19:30:00Z",
                },
                "latestTrade": {"p": 41.25, "s": 1, "t": "2026-08-14T19:29:00Z"},
                "impliedVolatility": 0.19,
                "greeks": {"delta": -0.48, "gamma": 0.009},
            }
        }
    }

    point = normalize_alpaca_option_surface(contracts, snapshots).points[0]

    assert point.bid == 41.0
    assert point.ask == 41.5
    assert point.trade_price == 41.25
    assert point.delta == pytest.approx(-0.48)
    assert point.gamma == pytest.approx(0.009)


def test_missing_snapshot_keeps_contract_and_marks_missing() -> None:
    contracts = {
        "option_contracts": [
            {
                "symbol": "SPXW260814P07800000",
                "underlying_symbol": "SPX",
                "expiration_date": "2026-08-14",
                "type": "put",
                "strike_price": "7800",
                "size": "100",
                "open_interest": "471",
            }
        ]
    }

    surface = normalize_alpaca_option_surface(contracts, {"snapshots": {}})

    assert len(surface.points) == 1
    assert surface.missing_snapshots == 1
    assert surface.points[0].gamma is None


def test_black_scholes_call_put_share_gamma_and_delta_relationship() -> None:
    call = black_scholes_greeks(
        option_type=OptionType.CALL,
        spot=7800.0,
        strike=7800.0,
        time_to_expiry_years=7 / 365,
        volatility=0.20,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )
    put = black_scholes_greeks(
        option_type=OptionType.PUT,
        spot=7800.0,
        strike=7800.0,
        time_to_expiry_years=7 / 365,
        volatility=0.20,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )

    assert call.price > 0
    assert put.price > 0
    assert call.gamma == pytest.approx(put.gamma)
    assert call.gamma > 0
    assert call.delta > 0
    assert put.delta < 0


def test_implied_volatility_round_trip() -> None:
    inputs = dict(
        option_type=OptionType.CALL,
        spot=7800.0,
        strike=7825.0,
        time_to_expiry_years=14 / 365,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )
    expected_volatility = 0.235
    price = black_scholes_greeks(volatility=expected_volatility, **inputs).price

    recovered = implied_volatility_from_price(option_price=price, **inputs)

    assert recovered == pytest.approx(expected_volatility, rel=1e-6)


def test_greek_enrichment_uses_alpaca_iv_when_greeks_are_missing() -> None:
    point = OptionSurfacePoint(
        symbol="SPXW260821C07800000",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.CALL,
        strike=7800.0,
        multiplier=100.0,
        open_interest=1000.0,
        implied_volatility=0.20,
    )

    result = enrich_missing_greeks(
        point,
        spot=7800.0,
        time_to_expiry_years=7 / 365,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )

    assert result.source == "alpaca_iv"
    assert result.point.gamma is not None and result.point.gamma > 0
    assert result.point.delta is not None and result.point.delta > 0


def test_greek_enrichment_can_recover_iv_from_quote_mid() -> None:
    theoretical = black_scholes_greeks(
        option_type=OptionType.PUT,
        spot=7800.0,
        strike=7800.0,
        time_to_expiry_years=7 / 365,
        volatility=0.22,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )
    point = OptionSurfacePoint(
        symbol="SPXW260821P07800000",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.PUT,
        strike=7800.0,
        multiplier=100.0,
        open_interest=500.0,
        bid=theoretical.price - 0.05,
        ask=theoretical.price + 0.05,
    )

    result = enrich_missing_greeks(
        point,
        spot=7800.0,
        time_to_expiry_years=7 / 365,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )

    assert result.source == "quote_implied_iv"
    assert result.implied_volatility == pytest.approx(0.22, rel=1e-5)
    assert result.point.gamma is not None and result.point.gamma > 0


def test_contract_exposure_has_exact_gax_gex_scaling() -> None:
    point = OptionSurfacePoint(
        symbol="SPXW260821C07800000",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.CALL,
        strike=7800.0,
        multiplier=100.0,
        open_interest=1000.0,
        delta=0.5,
        gamma=0.01,
    )

    exposure = contract_exposure(point, spot=7800.0)

    assert exposure is not None
    assert exposure.gamma_shares_per_point == pytest.approx(1000.0)
    assert exposure.gax_notional_per_point == pytest.approx(7_800_000.0)
    assert exposure.unsigned_gex_per_1pct == pytest.approx(608_400_000.0)
    assert exposure.unsigned_gex_per_1pct == pytest.approx(
        exposure.gax_notional_per_point * 7800.0 * 0.01
    )
    assert exposure.delta_notional == pytest.approx(390_000_000.0)


def test_put_heuristic_sign_is_negative_without_changing_unsigned_gamma() -> None:
    point = OptionSurfacePoint(
        symbol="SPXW260821P07800000",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.PUT,
        strike=7800.0,
        multiplier=100.0,
        open_interest=500.0,
        delta=-0.5,
        gamma=0.01,
    )

    exposure = contract_exposure(point, spot=7800.0)

    assert exposure is not None
    assert exposure.unsigned_gex_per_1pct > 0
    assert exposure.heuristic_signed_gax_per_point < 0
    assert exposure.heuristic_signed_gex_per_1pct < 0


def test_surface_aggregates_by_strike_and_counts_missing_gamma() -> None:
    call = OptionSurfacePoint(
        symbol="CALL",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.CALL,
        strike=7800.0,
        multiplier=100.0,
        open_interest=100.0,
        gamma=0.01,
        delta=0.5,
    )
    put = OptionSurfacePoint(
        symbol="PUT",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.PUT,
        strike=7800.0,
        multiplier=100.0,
        open_interest=50.0,
        gamma=0.01,
        delta=-0.5,
    )
    no_gamma = OptionSurfacePoint(
        symbol="NO_GAMMA",
        underlying_symbol="SPX",
        expiration_date=date(2026, 8, 21),
        option_type=OptionType.CALL,
        strike=7810.0,
        multiplier=100.0,
        open_interest=25.0,
    )

    surface = build_gex_surface([call, put, no_gamma], spot=7800.0)

    assert surface.contracts_seen == 3
    assert surface.contracts_used == 2
    assert surface.contracts_missing_gamma == 1
    assert len(surface.levels) == 1
    assert surface.levels[0].strike == 7800.0
    assert surface.levels[0].heuristic_signed_gex_per_1pct > 0


def test_non_positive_spot_is_rejected() -> None:
    with pytest.raises(ValueError, match="spot must be positive"):
        build_gex_surface([], spot=0)
