import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_session_collector.py"
SPEC = importlib.util.spec_from_file_location("gexy_session_collector", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

_ET = ZoneInfo("America/New_York")


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds):
        self.now += seconds


def _session_window():
    return MODULE.AlpacaMarketSession(
        session_date="2026-08-14",
        open_at=datetime(2026, 8, 14, 9, 30, tzinfo=_ET),
        close_at=datetime(2026, 8, 14, 16, 0, tzinfo=_ET),
    )


def test_run_cycle_skips_outside_session(monkeypatch):
    calls = []
    monkeypatch.setattr(MODULE, "alpaca_market_session_window", lambda _: None)
    monkeypatch.setattr(MODULE, "_run_script", lambda *args: calls.append(args))

    payload = MODULE.run_cycle()

    assert payload["status"] == "skipped"
    assert payload["reason"] == "outside_alpaca_market_session"
    assert payload["market_session_date"] is None
    assert payload["market_session_open_at"] is None
    assert payload["market_session_close_at"] is None
    assert payload["cycle_duration_seconds"] >= 0.0
    assert payload["cycle_started_at"]
    assert payload["cycle_finished_at"]
    assert calls == []


def test_run_cycle_reports_calendar_connectivity_error(monkeypatch):
    def fail_calendar(_):
        raise OSError("network unavailable")

    monkeypatch.setattr(MODULE, "alpaca_market_session_window", fail_calendar)

    payload = MODULE.run_cycle()

    assert payload["status"] == "error"
    assert payload["stage"] == "market_session"
    assert payload["reason"] == "calendar_unavailable"
    assert payload["error_type"] == "OSError"
    assert payload["market_session_close_at"] is None
    assert payload["cycle_duration_seconds"] >= 0.0


def test_run_cycle_outside_known_session_keeps_authoritative_window(monkeypatch):
    window = _session_window()
    monkeypatch.setattr(MODULE, "alpaca_market_session_window", lambda _: window)
    monkeypatch.setattr(window.__class__, "contains", lambda self, _: False)

    payload = MODULE.run_cycle()

    assert payload["status"] == "skipped"
    assert payload["market_session_date"] == "2026-08-14"
    assert payload["market_session_open_at"] == "2026-08-14T09:30:00-04:00"
    assert payload["market_session_close_at"] == "2026-08-14T16:00:00-04:00"


def test_run_cycle_resolves_before_predicting_and_records_session_window(monkeypatch):
    calls = []
    window = _session_window()
    monkeypatch.setattr(MODULE, "alpaca_market_session_window", lambda _: window)
    monkeypatch.setattr(window.__class__, "contains", lambda self, _: True)

    def fake_run(script_name, *args):
        calls.append((script_name, args))
        if script_name == "gexy_resolve_due.py":
            return {"status": "ok", "resolved": 1, "exit_code": 0}
        return {
            "status": "ok",
            "journaled_forecasts": 4,
            "journaled_fine_shadow_forecasts": 60,
            "exit_code": 0,
        }

    monkeypatch.setattr(MODULE, "_run_script", fake_run)

    payload = MODULE.run_cycle(tolerance_seconds=75)

    assert payload["status"] == "ok"
    assert calls[0] == ("gexy_resolve_due.py", ("--tolerance-seconds", "75"))
    assert calls[1] == ("gexy_live_predict.py", ("--horizon", "30"))
    assert payload["prediction"]["journaled_fine_shadow_forecasts"] == 60
    assert payload["market_session_date"] == "2026-08-14"
    assert payload["market_session_open_at"] == "2026-08-14T09:30:00-04:00"
    assert payload["market_session_close_at"] == "2026-08-14T16:00:00-04:00"
    assert payload["cycle_duration_seconds"] >= 0.0


def test_run_cycle_stops_if_resolver_fails(monkeypatch):
    calls = []
    window = _session_window()
    monkeypatch.setattr(MODULE, "alpaca_market_session_window", lambda _: window)
    monkeypatch.setattr(window.__class__, "contains", lambda self, _: True)

    def fake_run(script_name, *args):
        calls.append((script_name, args))
        return {"status": "error", "exit_code": 2}

    monkeypatch.setattr(MODULE, "_run_script", fake_run)

    payload = MODULE.run_cycle()

    assert payload["status"] == "error"
    assert payload["stage"] == "resolve_due"
    assert payload["market_session_close_at"] == "2026-08-14T16:00:00-04:00"
    assert [name for name, _ in calls] == ["gexy_resolve_due.py"]


def test_run_loop_waits_before_open_then_collects_and_stops_after_close(monkeypatch):
    payloads = iter([
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
        {"status": "ok"},
        {"status": "ok"},
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
    ])
    clock = FakeClock()
    monkeypatch.setattr(MODULE, "run_cycle", lambda **_: next(payloads))
    monkeypatch.setattr(MODULE.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(MODULE.time, "sleep", clock.sleep)

    exit_code = MODULE.run_loop(interval_seconds=60, tolerance_seconds=90)

    assert exit_code == 0
    assert clock.sleeps == [60.0, 60.0, 60.0]


def test_run_loop_retries_transient_error_then_recovers(monkeypatch):
    payloads = iter([
        {"status": "error", "stage": "market_session"},
        {"status": "ok"},
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
    ])
    clock = FakeClock()
    monkeypatch.setattr(MODULE, "run_cycle", lambda **_: next(payloads))
    monkeypatch.setattr(MODULE.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(MODULE.time, "sleep", clock.sleep)

    exit_code = MODULE.run_loop(interval_seconds=60, tolerance_seconds=90)

    assert exit_code == 0
    assert clock.sleeps == [60.0, 60.0]


def test_scheduler_subtracts_cycle_runtime_from_sleep(monkeypatch):
    clock = FakeClock()
    payloads = iter([
        {"status": "ok"},
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
    ])

    def fake_cycle(**_):
        payload = next(payloads)
        clock.advance(15.0)
        return payload

    monkeypatch.setattr(MODULE, "run_cycle", fake_cycle)
    monkeypatch.setattr(MODULE.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(MODULE.time, "sleep", clock.sleep)

    exit_code = MODULE.run_loop(interval_seconds=60, tolerance_seconds=90)

    assert exit_code == 0
    assert clock.sleeps == [45.0]
    assert clock.now == 75.0


def test_scheduler_skips_missed_tick_after_overrun_without_burst(monkeypatch, capsys):
    clock = FakeClock()
    payloads = iter([
        {"status": "ok"},
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
    ])

    def fake_cycle(**_):
        payload = next(payloads)
        clock.advance(75.0)
        return payload

    monkeypatch.setattr(MODULE, "run_cycle", fake_cycle)
    monkeypatch.setattr(MODULE.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(MODULE.time, "sleep", clock.sleep)

    exit_code = MODULE.run_loop(interval_seconds=60, tolerance_seconds=90)

    assert exit_code == 0
    assert clock.sleeps == [45.0]
    output = capsys.readouterr().out
    assert '"missed_intervals": 1' in output
    assert '"overrun_seconds": 15.0' in output
