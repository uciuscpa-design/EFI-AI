from datetime import datetime, timezone

from packages.gexy.alpaca_provider import (
    black_scholes_gamma,
    implied_volatility,
    infer_forward_spot,
    infer_forward_spot_with_provenance,
)


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


def test_parity_provenance_tracks_only_selected_median_pair_timestamps():
    contracts = {
        "C1": {"expiration_date": "2026-08-21", "strike_price": 7740, "type": "call"},
        "P1": {"expiration_date": "2026-08-21", "strike_price": 7740, "type": "put"},
        "C2": {"expiration_date": "2026-08-21", "strike_price": 7750, "type": "call"},
        "P2": {"expiration_date": "2026-08-21", "strike_price": 7750, "type": "put"},
        "C3": {"expiration_date": "2026-08-21", "strike_price": 7760, "type": "call"},
        "P3": {"expiration_date": "2026-08-21", "strike_price": 7760, "type": "put"},
    }
    chain = {
        "C1": {"latest_quote": {"bid_price": 56.5, "ask_price": 57.5, "timestamp": "2026-08-14T17:30:00.100Z"}},
        "P1": {"latest_quote": {"bid_price": 42.5, "ask_price": 43.5, "timestamp": "2026-08-14T17:30:00.200Z"}},
        "C2": {"latest_quote": {"bid_price": 47.0, "ask_price": 48.0, "timestamp": "2026-08-14T17:30:00.300Z"}},
        "P2": {"latest_quote": {"bid_price": 44.0, "ask_price": 45.0, "timestamp": "2026-08-14T17:30:00.400Z"}},
        "C3": {"latest_quote": {"bid_price": 38.0, "ask_price": 39.0, "timestamp": "2026-08-14T17:30:00.500Z"}},
        "P3": {"latest_quote": {"bid_price": 49.0, "ask_price": 50.0, "timestamp": "2026-08-14T17:30:00.600Z"}},
    }

    estimate = infer_forward_spot_with_provenance(chain, contracts)

    assert estimate.spot == 7753.0
    assert estimate.strike == 7750.0
    assert estimate.expiration_date == "2026-08-21"
    assert estimate.quote_times == (
        datetime(2026, 8, 14, 17, 30, 0, 300000, tzinfo=timezone.utc),
        datetime(2026, 8, 14, 17, 30, 0, 400000, tzinfo=timezone.utc),
    )
    assert estimate.quote_time_min == estimate.quote_times[0]
    assert estimate.quote_time_max == estimate.quote_times[1]
