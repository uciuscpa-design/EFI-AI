from __future__ import annotations

import pandas as pd
import pytest

from packages.gexy.forward_greeks import black76_greeks
from packages.gexy.models import OptionType
from packages.gexy.tradeflow_hedge import (
    aggregate_hedge_flow_minutes,
    apply_dealer_hedge_proxy,
    build_symbol_minute_greeks,
    join_hedge_flow_to_replay,
)


def _call_price() -> float:
    minutes_per_year = 365.0 * 24.0 * 60.0
    return black76_greeks(
        option_type=OptionType.CALL,
        forward=100.0,
        strike=100.0,
        time_to_expiry_years=60.0 / minutes_per_year,
        volatility=0.20,
        discount_factor=1.0,
    ).price


def test_symbol_minute_greeks_solve_from_completed_minute_nbbo() -> None:
    price = _call_price()
    classified = pd.DataFrame(
        {
            "ts_recv": ["2026-08-12T13:30:10Z", "2026-08-12T13:30:40Z"],
            "symbol": ["SPXW TEST", "SPXW TEST"],
            "instrument_class": ["C", "C"],
            "strike_price": [100.0, 100.0],
            "bid_px_00": [price, price],
            "ask_px_00": [price, price],
        }
    )
    replay = pd.DataFrame(
        {
            "timestamp": ["2026-08-12T13:30:00Z"],
            "forward": [100.0],
            "discount_factor_fit": [1.0],
            "time_to_expiry_minutes": [60.0],
        }
    )

    result = build_symbol_minute_greeks(classified, replay)

    assert len(result) == 1
    row = result.iloc[0]
    assert bool(row["greek_solved"])
    assert row["implied_volatility"] == pytest.approx(0.20, rel=1e-4)
    assert row["delta_forward"] > 0
    assert row["gamma_forward"] > 0
    assert row["timestamp"] == pd.Timestamp("2026-08-12T13:31:00Z")


def test_dealer_proxy_signs_call_and_put_delta_but_gamma_tracks_aggressor_side() -> None:
    classified = pd.DataFrame(
        {
            "ts_recv": ["2026-08-12T13:30:10Z", "2026-08-12T13:30:20Z"],
            "symbol": ["CALL", "PUT"],
            "instrument_class": ["C", "P"],
            "size": [2.0, 3.0],
            "signed_side": [1.0, 1.0],
        }
    )
    greeks = pd.DataFrame(
        {
            "flow_minute": [pd.Timestamp("2026-08-12T13:30:00Z")] * 2,
            "symbol": ["CALL", "PUT"],
            "forward": [100.0, 100.0],
            "delta_forward": [0.50, -0.40],
            "gamma_forward": [0.02, 0.03],
            "greek_solved": [True, True],
        }
    )

    weighted = apply_dealer_hedge_proxy(classified, greeks)
    call = weighted.loc[weighted["symbol"] == "CALL"].iloc[0]
    put = weighted.loc[weighted["symbol"] == "PUT"].iloc[0]

    assert call["hedge_delta_units"] == pytest.approx(100.0)
    assert put["hedge_delta_units"] == pytest.approx(-120.0)
    assert call["hedge_gamma_units_per_point"] == pytest.approx(4.0)
    assert put["hedge_gamma_units_per_point"] == pytest.approx(9.0)


def test_aggregate_and_join_preserve_m_plus_one_causality() -> None:
    weighted = pd.DataFrame(
        {
            "flow_minute": [pd.Timestamp("2026-08-12T13:30:00Z")],
            "symbol": ["CALL"],
            "instrument_class": ["C"],
            "size": [10.0],
            "signed_side": [1.0],
            "hedge_greek_available": [True],
            "hedge_delta_units": [500.0],
            "hedge_delta_notional": [50_000.0],
            "hedge_gamma_units_per_point": [20.0],
            "hedge_gax_notional_per_point": [2_000.0],
            "hedge_gex_notional_per_1pct": [2_000.0],
        }
    )
    minute = aggregate_hedge_flow_minutes(weighted)
    assert minute.iloc[0]["timestamp"] == pd.Timestamp("2026-08-12T13:31:00Z")

    replay = pd.DataFrame(
        {
            "timestamp": [
                "2026-08-12T13:31:00Z",
                "2026-08-12T13:32:00Z",
            ],
            "forward": [100.0, 101.0],
        }
    )
    joined = join_hedge_flow_to_replay(minute, replay, horizons_minutes=(1,))

    assert bool(joined.iloc[0]["replay_match"])
    assert joined.iloc[0]["forward_return_1m_bps"] == pytest.approx(100.0)
