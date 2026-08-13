from datetime import datetime, timezone

from packages.gexy.alpaca_provider import black_scholes_gamma, implied_volatility, infer_forward_spot


def test_iv_round_trip_and_gamma_positive():
    s = 7750.0
    k = 7750.0
    t = 9 / 365
    price = 58.6
    iv = implied_volatility("call", price, s, k, t)
    assert iv is not None
    assert 0.01 < iv < 1.0
    gamma = black_scholes_gamma(s, k, t, 0.0, iv)
    assert gamma > 0


def test_parity_reference_uses_matched_call_put_mids():
    contracts = {
        "C": {"expiration_date": "2026-08-21", "strike_price": 7750, "type": "call"},
        "P": {"expiration_date": "2026-08-21", "strike_price": 7750, "type": "put"},
    }
    chain = {
        "C": {"latest_quote": {"bid_price": 47.0, "ask_price": 48.0}},
        "P": {"latest_quote": {"bid_price": 44.0, "ask_price": 45.0}},
    }
    assert infer_forward_spot(chain, contracts) == 7753.0
