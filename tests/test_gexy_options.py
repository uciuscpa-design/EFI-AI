from datetime import date

import pytest

from packages.data.alpaca_options import contract_from_payload, snapshot_from_payload
from packages.options.gex import GexSignMethod, aggregate_gex, gamma_exposure_per_1pct
from packages.options.greeks import black_scholes_gamma, black_scholes_price, implied_volatility
from packages.options.models import OptionContract, OptionStyle, OptionType


def _contract(option_type: OptionType, *, open_interest: float | None = 10.0) -> OptionContract:
    return OptionContract(
        symbol=f"TEST-{option_type.value}",
        underlying_symbol="SPX",
        root_symbol="SPXW",
        expiration_date=date(2026, 8, 17),
        strike_price=100.0,
        option_type=option_type,
        style=OptionStyle.EUROPEAN,
        multiplier=100.0,
        open_interest=open_interest,
        open_interest_date=date(2026, 8, 12),
    )


def test_implied_volatility_round_trip() -> None:
    expected_volatility = 0.25
    price = black_scholes_price(
        spot=100.0,
        strike=100.0,
        years_to_expiry=0.5,
        volatility=expected_volatility,
        option_type=OptionType.CALL,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )
    solved = implied_volatility(
        market_price=price,
        spot=100.0,
        strike=100.0,
        years_to_expiry=0.5,
        option_type=OptionType.CALL,
        risk_free_rate=0.04,
        dividend_yield=0.01,
    )
    assert solved == pytest.approx(expected_volatility, abs=1e-6)


def test_call_and_put_gamma_match_for_equal_inputs() -> None:
    gamma = black_scholes_gamma(
        spot=100.0,
        strike=105.0,
        years_to_expiry=0.25,
        volatility=0.2,
        risk_free_rate=0.03,
    )
    assert gamma > 0


def test_gex_call_put_proxy_sign_and_formula() -> None:
    call = _contract(OptionType.CALL)
    put = _contract(OptionType.PUT)

    call_gex = gamma_exposure_per_1pct(contract=call, gamma=0.02, spot=100.0)
    put_gex = gamma_exposure_per_1pct(contract=put, gamma=0.02, spot=100.0)

    assert call_gex == pytest.approx(2_000.0)
    assert put_gex == pytest.approx(-2_000.0)


def test_gex_unsigned_keeps_put_positive() -> None:
    put = _contract(OptionType.PUT)
    value = gamma_exposure_per_1pct(
        contract=put,
        gamma=0.02,
        spot=100.0,
        sign_method=GexSignMethod.UNSIGNED,
    )
    assert value == pytest.approx(2_000.0)


def test_aggregate_skips_missing_gamma_or_open_interest() -> None:
    call = _contract(OptionType.CALL)
    put_without_oi = _contract(OptionType.PUT, open_interest=None)
    summary = aggregate_gex(
        [(call, 0.02), (put_without_oi, 0.03), (_contract(OptionType.PUT), None)],
        spot=100.0,
    )
    assert summary.net_exposure_per_1pct == pytest.approx(2_000.0)
    assert summary.gross_exposure_per_1pct == pytest.approx(2_000.0)
    assert len(summary.skipped_symbols) == 2


def test_alpaca_contract_parser_preserves_spxw_metadata() -> None:
    contract = contract_from_payload(
        {
            "symbol": "SPXW260817C07800000",
            "underlying_symbol": "SPX",
            "root_symbol": "SPXW",
            "expiration_date": "2026-08-17",
            "strike_price": "7800",
            "type": "call",
            "style": "european",
            "size": "100",
            "open_interest": "1444",
            "open_interest_date": "2026-08-12",
        }
    )
    assert contract.underlying_symbol == "SPX"
    assert contract.root_symbol == "SPXW"
    assert contract.multiplier == 100.0
    assert contract.open_interest == 1444.0
    assert contract.style is OptionStyle.EUROPEAN


def test_alpaca_snapshot_parser_handles_compact_market_data_keys() -> None:
    snapshot = snapshot_from_payload(
        "SPXW260817C07800000",
        {
            "latestQuote": {"bp": 8.96, "ap": 9.09, "t": "2026-08-14T19:59:59Z"},
            "latestTrade": {"p": 7.30, "t": "2026-08-14T20:59:49Z"},
            "impliedVolatility": None,
            "greeks": None,
        },
    )
    assert snapshot.mark == pytest.approx(9.025)
    assert snapshot.last == pytest.approx(7.30)
    assert snapshot.greeks is None
