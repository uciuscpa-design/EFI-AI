from __future__ import annotations

import pandas as pd

from packages.gexy.tradeflow_window_regime import (
    assign_session_window,
    summarize_window_days,
)


def test_assign_session_window_uses_flow_minute_new_york_clock() -> None:
    frame = pd.DataFrame(
        {
            "flow_minute": [
                "2026-08-13T13:30:00Z",  # 09:30 ET
                "2026-08-13T13:59:00Z",  # 09:59 ET
                "2026-08-13T14:00:00Z",  # 10:00 ET, outside
                "2026-08-13T19:30:00Z",  # 15:30 ET
                "2026-08-13T19:59:00Z",  # 15:59 ET
                "2026-08-13T20:00:00Z",  # 16:00 ET, outside
            ]
        }
    )

    result = assign_session_window(frame)

    assert result["session_window"].astype(object).where(result["session_window"].notna(), None).tolist() == [
        "opening",
        "opening",
        None,
        "closing",
        "closing",
        None,
    ]


def test_summarize_window_days_keeps_windows_separate() -> None:
    frame = pd.DataFrame(
        {
            "session_window": ["opening", "opening", "closing", "closing"],
            "horizon_minutes": [15, 15, 15, 15],
            "hedge_partial_spearman_controlling_momentum_and_raw": [-0.3, -0.2, 0.1, -0.1],
        }
    )

    result = summarize_window_days(frame)
    opening = result.loc[result["session_window"] == "opening"].iloc[0]
    closing = result.loc[result["session_window"] == "closing"].iloc[0]

    assert opening["negative_days"] == 2
    assert opening["median_partial_spearman"] == -0.25
    assert closing["negative_days"] == 1
    assert closing["median_partial_spearman"] == 0.0
