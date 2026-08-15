from __future__ import annotations

import pandas as pd
import pytest

from packages.gexy.tradeflow_features import aggregate_completed_minute_flow, join_flow_to_replay


def _classified_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ts_recv": [
                "2026-08-12T13:30:01Z",
                "2026-08-12T13:30:30Z",
                "2026-08-12T13:30:59Z",
                "2026-08-12T13:31:10Z",
            ],
            "symbol": ["CALL1", "PUT1", "CALL1", "PUT1"],
            "size": [10, 5, 2, 4],
            "instrument_class": ["C", "P", "C", "P"],
            "signed_side": [1, -1, 0, 1],
            "signed_contracts": [10, -5, 0, 4],
            "premium_notional": [1000.0, 500.0, 200.0, 800.0],
            "signed_premium_notional": [1000.0, -500.0, 0.0, 800.0],
        }
    )


def test_completed_minute_flow_is_available_one_minute_later() -> None:
    result = aggregate_completed_minute_flow(_classified_frame())

    assert result["flow_minute"].tolist() == [
        pd.Timestamp("2026-08-12T13:30:00Z"),
        pd.Timestamp("2026-08-12T13:31:00Z"),
    ]
    assert result["timestamp"].tolist() == [
        pd.Timestamp("2026-08-12T13:31:00Z"),
        pd.Timestamp("2026-08-12T13:32:00Z"),
    ]


def test_completed_minute_flow_aggregates_signed_and_quality_features() -> None:
    result = aggregate_completed_minute_flow(_classified_frame())
    first = result.iloc[0]

    assert first["flow_trade_records"] == 3
    assert first["flow_unique_symbols"] == 2
    assert first["flow_classified_trade_records"] == 2
    assert first["flow_unknown_trade_records"] == 1
    assert first["flow_classification_rate"] == pytest.approx(2 / 3)
    assert first["flow_contract_volume"] == 17
    assert first["flow_classified_contract_volume"] == 15
    assert first["flow_unknown_contract_volume"] == 2
    assert first["flow_net_signed_contracts"] == 5
    assert first["flow_contract_imbalance"] == pytest.approx(5 / 15)
    assert first["flow_gross_premium_notional"] == 1700
    assert first["flow_classified_premium_notional"] == 1500
    assert first["flow_unknown_premium_notional"] == 200
    assert first["flow_net_signed_premium_notional"] == 500
    assert first["flow_premium_imbalance"] == pytest.approx(500 / 1500)
    assert first["flow_buy_contract_volume"] == 10
    assert first["flow_sell_contract_volume"] == 5
    assert first["flow_signed_call_contracts"] == 10
    assert first["flow_signed_put_contracts"] == -5
    assert first["flow_signed_call_premium_notional"] == 1000
    assert first["flow_signed_put_premium_notional"] == -500


def test_join_flow_to_replay_uses_availability_timestamp_and_builds_labels() -> None:
    flow = aggregate_completed_minute_flow(_classified_frame())
    replay = pd.DataFrame(
        {
            "timestamp": [
                "2026-08-12T13:31:00Z",
                "2026-08-12T13:32:00Z",
                "2026-08-12T13:33:00Z",
            ],
            "forward": [7760.0, 7761.0, 7763.0],
            "total_gax_forward_proxy_per_point": [1.0, 2.0, 3.0],
        }
    )

    joined = join_flow_to_replay(flow, replay, horizons_minutes=(1,))

    assert joined["replay_match"].tolist() == [True, True]
    assert joined.iloc[0]["forward"] == 7760.0
    assert joined.iloc[0]["forward_t_plus_1m"] == 7761.0
    assert joined.iloc[0]["forward_move_1m_points"] == 1.0
    assert joined.iloc[1]["forward_t_plus_1m"] == 7763.0


def test_join_flow_marks_missing_replay_minute_without_nearest_time_fill() -> None:
    flow = aggregate_completed_minute_flow(_classified_frame())
    replay = pd.DataFrame(
        {
            "timestamp": ["2026-08-12T13:31:00Z"],
            "forward": [7760.0],
        }
    )

    joined = join_flow_to_replay(flow, replay, horizons_minutes=(1,))

    assert joined["replay_match"].tolist() == [True, False]
    assert pd.isna(joined.iloc[1]["forward"])
