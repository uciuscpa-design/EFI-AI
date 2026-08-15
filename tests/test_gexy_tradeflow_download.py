from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pytest

from scripts.gexy_tradeflow_download import (
    ABSOLUTE_MAX_COST,
    WindowPlan,
    _assert_outputs_absent,
    _download_window,
    _total_cost,
    _validate_cost_cap,
    _window_output_path,
)


class _FakeTimeseries:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_range(self, **kwargs: object):
        self.calls.append(kwargs)
        Path(str(kwargs["path"])).write_bytes(b"dbn")
        return object()


class _FakeClient:
    def __init__(self) -> None:
        self.timeseries = _FakeTimeseries()


def _plan(tmp_path: Path, cost: float = 1.25) -> WindowPlan:
    return WindowPlan(
        window=(time(9, 30), time(10, 0)),
        cost=cost,
        output_path=tmp_path / "pilot.dbn.zst",
    )


def test_window_output_path_is_bounded_and_tcbbo(tmp_path: Path) -> None:
    path = _window_output_path(
        tmp_path,
        date(2026, 8, 12),
        (time(15, 30), time(16, 0)),
    )
    assert path.name == "gexy_spxw_2026-08-12_1530_1600_tcbbo.dbn.zst"


def test_total_cost_sums_windows(tmp_path: Path) -> None:
    plans = (
        _plan(tmp_path, 2.038655),
        WindowPlan(
            window=(time(15, 30), time(16, 0)),
            cost=1.690355,
            output_path=tmp_path / "close.dbn.zst",
        ),
    )
    assert _total_cost(plans) == pytest.approx(3.729010)


def test_cost_cap_accepts_pilot_under_five_dollars() -> None:
    _validate_cost_cap(total_cost=3.729010, max_cost=5.0)


def test_cost_cap_blocks_estimate_above_requested_cap() -> None:
    with pytest.raises(ValueError, match="exceeds --max-cost"):
        _validate_cost_cap(total_cost=3.729010, max_cost=3.50)


def test_requested_cap_cannot_exceed_absolute_ceiling() -> None:
    with pytest.raises(ValueError, match="hard safety ceiling"):
        _validate_cost_cap(total_cost=3.0, max_cost=ABSOLUTE_MAX_COST + 0.01)


def test_existing_output_blocks_download(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    plan.output_path.write_bytes(b"existing")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        _assert_outputs_absent((plan,))


def test_existing_partial_blocks_download(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    partial = plan.output_path.with_suffix(plan.output_path.suffix + ".partial")
    partial.write_bytes(b"partial")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        _assert_outputs_absent((plan,))


def test_download_window_requests_exact_tcbbo_scope_and_promotes_partial(tmp_path: Path) -> None:
    client = _FakeClient()
    plan = _plan(tmp_path)

    _download_window(
        client,
        day=date(2026, 8, 12),
        symbols=["SPXW  260812C07760000"],
        plan=plan,
    )

    assert plan.output_path.read_bytes() == b"dbn"
    partial = plan.output_path.with_suffix(plan.output_path.suffix + ".partial")
    assert not partial.exists()
    assert client.timeseries.calls == [
        {
            "dataset": "OPRA.PILLAR",
            "schema": "tcbbo",
            "stype_in": "raw_symbol",
            "symbols": ["SPXW  260812C07760000"],
            "start": "2026-08-12T09:30:00-04:00",
            "end": "2026-08-12T10:00:00-04:00",
            "path": str(partial),
        }
    ]
