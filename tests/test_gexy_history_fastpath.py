from __future__ import annotations

import pandas as pd

from packages.gexy.rolling import eligible_history, inner_purged_split


def _reference_history(
    frame: pd.DataFrame,
    *,
    prediction_time: pd.Timestamp,
    horizon_minutes: int,
    max_rows: int,
) -> pd.DataFrame:
    horizon = pd.Timedelta(minutes=horizon_minutes)
    ordered = frame.sort_values("timestamp").copy()
    timestamps = pd.to_datetime(ordered["timestamp"], utc=True)
    known = ordered.loc[timestamps + horizon < prediction_time].copy()
    return known.tail(max_rows).reset_index(drop=True)


def _reference_inner(
    history: pd.DataFrame,
    *,
    horizon_minutes: int,
    validation_rows: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    ordered = history.sort_values("timestamp").reset_index(drop=True)
    validation = ordered.tail(validation_rows).copy()
    validation_start = pd.Timestamp(validation.iloc[0]["timestamp"])
    horizon = pd.Timedelta(minutes=horizon_minutes)
    timestamps = pd.to_datetime(ordered["timestamp"], utc=True)
    fit = ordered.loc[timestamps + horizon < validation_start].copy()
    return fit, validation, validation_start


def _frame() -> pd.DataFrame:
    timestamps = pd.date_range("2026-08-13T13:31:00Z", periods=240, freq="1min")
    frame = pd.DataFrame({"timestamp": timestamps, "value": range(len(timestamps))})
    # Exercise the fallback ordering path too.
    return pd.concat([frame.iloc[120:], frame.iloc[:120]], ignore_index=True)


def test_eligible_history_fastpath_matches_original_semantics() -> None:
    frame = _frame()
    prediction_time = pd.Timestamp("2026-08-13T16:01:00Z")

    expected = _reference_history(
        frame,
        prediction_time=prediction_time,
        horizon_minutes=30,
        max_rows=180,
    )
    actual = eligible_history(
        frame,
        prediction_time=prediction_time,
        horizon_minutes=30,
        max_rows=180,
    )

    pd.testing.assert_frame_equal(actual, expected)


def test_eligible_history_preserves_strict_boundary() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2026-08-13T14:29:00Z",
                    "2026-08-13T14:30:00Z",
                    "2026-08-13T14:31:00Z",
                ],
                utc=True,
            ),
            "value": [29, 30, 31],
        }
    )
    prediction_time = pd.Timestamp("2026-08-13T15:00:00Z")

    actual = eligible_history(
        frame,
        prediction_time=prediction_time,
        horizon_minutes=30,
        max_rows=180,
    )

    # 14:30 + 30m == 15:00 is not yet eligible because the rule is strict <.
    assert actual["value"].tolist() == [29]


def test_inner_purged_fastpath_matches_original_semantics() -> None:
    history = _reference_history(
        _frame(),
        prediction_time=pd.Timestamp("2026-08-13T17:00:00Z"),
        horizon_minutes=15,
        max_rows=180,
    )
    expected_fit, expected_validation, expected_start = _reference_inner(
        history,
        horizon_minutes=15,
        validation_rows=30,
    )

    actual = inner_purged_split(
        history,
        horizon_minutes=15,
        validation_rows=30,
        min_fit_rows=40,
    )

    pd.testing.assert_frame_equal(actual.fit, expected_fit)
    pd.testing.assert_frame_equal(actual.validation, expected_validation)
    assert actual.validation_start == expected_start
