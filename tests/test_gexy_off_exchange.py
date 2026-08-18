from __future__ import annotations

import pandas as pd
import pytest

from packages.gexy.off_exchange import (
    add_causal_large_print_flags,
    aggregate_completed_minute_off_exchange,
    normalize_off_exchange_trades,
)


def _raw_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts_recv": [
                "2026-08-17T13:30:05Z",
                "2026-08-17T13:30:20Z",
                "2026-08-17T13:30:40Z",
                "2026-08-17T13:31:03Z",
                "2026-08-17T13:31:30Z",
            ],
            "symbol": ["SPY", "SPY", "AAPL", "SPY", "SPY"],
            "price": [650.00, 650.00, 230.00, 650.25, 650.25],
            "size": [100, 200, 50, 1000, 100],
            "venue": ["TRF", "TRF", "XNAS", "TRF", "TRF"],
        }
    )


def test_normalize_requires_explicit_off_exchange_identification() -> None:
    raw = _raw_trades()
    with pytest.raises(ValueError, match="identification must be explicit"):
        normalize_off_exchange_trades(
            raw,
            available_at_col="ts_recv",
            symbol_col="symbol",
            price_col="price",
            size_col="size",
        )


def test_normalize_filters_to_explicit_trf_venues_without_side_inference() -> None:
    normalized = normalize_off_exchange_trades(
        _raw_trades(),
        available_at_col="ts_recv",
        symbol_col="symbol",
        price_col="price",
        size_col="size",
        venue_col="venue",
        off_exchange_venues={"TRF"},
        source="fixture",
    )

    assert len(normalized) == 4
    assert set(normalized["reporting_venue"]) == {"TRF"}
    assert normalized["off_exchange_observed"].all()
    assert "signed_side" not in normalized.columns
    assert "buyer" not in normalized.columns
    assert "seller" not in normalized.columns
    assert normalized.iloc[0]["notional"] == pytest.approx(65_000.0)


def test_large_print_flags_use_only_prior_prints() -> None:
    raw = pd.DataFrame(
        {
            "available": pd.date_range("2026-08-17T13:30:00Z", periods=6, freq="s"),
            "symbol": ["SPY"] * 6,
            "price": [650.0] * 6,
            "size": [100, 100, 100, 100, 100, 1000],
            "venue": ["TRF"] * 6,
        }
    )
    normalized = normalize_off_exchange_trades(
        raw,
        available_at_col="available",
        symbol_col="symbol",
        price_col="price",
        size_col="size",
        venue_col="venue",
        off_exchange_venues={"TRF"},
    )
    flagged = add_causal_large_print_flags(
        normalized,
        lookback_prints=5,
        min_periods=5,
        quantile=0.95,
    )

    assert not flagged.loc[:4, "large_print_eligible"].any()
    assert flagged.loc[5, "large_print_eligible"]
    assert flagged.loc[5, "large_print_threshold"] == pytest.approx(100.0)
    assert flagged.loc[5, "is_large_print"]


def test_completed_minute_features_are_available_at_m_plus_one() -> None:
    normalized = normalize_off_exchange_trades(
        _raw_trades(),
        available_at_col="ts_recv",
        symbol_col="symbol",
        price_col="price",
        size_col="size",
        venue_col="venue",
        off_exchange_venues={"TRF"},
    )
    flagged = add_causal_large_print_flags(
        normalized,
        lookback_prints=2,
        min_periods=1,
        quantile=0.50,
    )
    features = aggregate_completed_minute_off_exchange(
        flagged,
        anomaly_lookback_minutes=2,
        anomaly_min_periods=1,
    )

    assert list(features["offx_minute"].dt.strftime("%H:%M")) == ["13:30", "13:31"]
    assert list(features["timestamp"].dt.strftime("%H:%M")) == ["13:31", "13:32"]
    assert features.loc[0, "offx_trade_records"] == 2
    assert features.loc[0, "offx_share_volume"] == pytest.approx(300.0)
    assert features.loc[0, "offx_repeated_level_groups"] == 1
    assert features.loc[0, "offx_repeated_level_volume"] == pytest.approx(300.0)


def test_future_print_does_not_change_prior_large_print_classification() -> None:
    base = pd.DataFrame(
        {
            "available": pd.date_range("2026-08-17T13:30:00Z", periods=7, freq="s"),
            "symbol": ["SPY"] * 7,
            "price": [650.0] * 7,
            "size": [100, 110, 90, 105, 95, 1000, 120],
            "venue": ["TRF"] * 7,
        }
    )
    normalized = normalize_off_exchange_trades(
        base,
        available_at_col="available",
        symbol_col="symbol",
        price_col="price",
        size_col="size",
        venue_col="venue",
        off_exchange_venues={"TRF"},
    )
    first = add_causal_large_print_flags(
        normalized,
        lookback_prints=5,
        min_periods=5,
        quantile=0.95,
    )

    changed = normalized.copy()
    changed.loc[6, "size"] = 100_000
    changed.loc[6, "notional"] = changed.loc[6, "size"] * changed.loc[6, "price"]
    second = add_causal_large_print_flags(
        changed,
        lookback_prints=5,
        min_periods=5,
        quantile=0.95,
    )

    assert first.loc[5, "large_print_threshold"] == pytest.approx(second.loc[5, "large_print_threshold"])
    assert bool(first.loc[5, "is_large_print"]) == bool(second.loc[5, "is_large_print"])
