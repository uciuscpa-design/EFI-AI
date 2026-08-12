from datetime import datetime, timedelta

from packages.gexy.replay_labels import PricePoint, build_forward_labels


def test_forward_labels_use_future_prices_only():
    t0 = datetime(2026, 8, 10, 10, 0)
    origin = PricePoint(t0, 100.0)
    prices = [
        PricePoint(t0 - timedelta(minutes=1), 999.0),
        PricePoint(t0 + timedelta(minutes=1), 101.0),
        PricePoint(t0 + timedelta(minutes=5), 105.0),
    ]
    labels = build_forward_labels([origin], prices, (1, 5))
    assert [x.return_pct for x in labels] == [1.0, 5.0]


def test_missing_horizon_is_null():
    t0 = datetime(2026, 8, 10, 10, 0)
    labels = build_forward_labels(
        [PricePoint(t0, 100.0)],
        [PricePoint(t0 + timedelta(minutes=1), 101.0)],
        (5,),
    )
    assert labels[0].future_price is None
    assert labels[0].return_pct is None
