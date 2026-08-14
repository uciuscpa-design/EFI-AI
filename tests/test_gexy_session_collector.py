import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_session_collector.py"
SPEC = importlib.util.spec_from_file_location("gexy_session_collector", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_run_cycle_skips_outside_session(monkeypatch):
    calls = []
    monkeypatch.setattr(MODULE, "is_alpaca_market_session", lambda _: False)
    monkeypatch.setattr(MODULE, "_run_script", lambda *args: calls.append(args))

    payload = MODULE.run_cycle()

    assert payload["status"] == "skipped"
    assert payload["reason"] == "outside_alpaca_market_session"
    assert calls == []


def test_run_cycle_reports_calendar_connectivity_error(monkeypatch):
    def fail_calendar(_):
        raise OSError("network unavailable")

    monkeypatch.setattr(MODULE, "is_alpaca_market_session", fail_calendar)

    payload = MODULE.run_cycle()

    assert payload["status"] == "error"
    assert payload["stage"] == "market_session"
    assert payload["reason"] == "calendar_unavailable"
    assert payload["error_type"] == "OSError"


def test_run_cycle_resolves_before_predicting(monkeypatch):
    calls = []
    monkeypatch.setattr(MODULE, "is_alpaca_market_session", lambda _: True)

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


def test_run_cycle_stops_if_resolver_fails(monkeypatch):
    calls = []
    monkeypatch.setattr(MODULE, "is_alpaca_market_session", lambda _: True)

    def fake_run(script_name, *args):
        calls.append((script_name, args))
        return {"status": "error", "exit_code": 2}

    monkeypatch.setattr(MODULE, "_run_script", fake_run)

    payload = MODULE.run_cycle()

    assert payload["status"] == "error"
    assert payload["stage"] == "resolve_due"
    assert [name for name, _ in calls] == ["gexy_resolve_due.py"]


def test_run_loop_waits_before_open_then_collects_and_stops_after_close(monkeypatch):
    payloads = iter([
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
        {"status": "ok"},
        {"status": "ok"},
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
    ])
    sleeps = []
    monkeypatch.setattr(MODULE, "run_cycle", lambda **_: next(payloads))
    monkeypatch.setattr(MODULE.time, "sleep", lambda seconds: sleeps.append(seconds))

    exit_code = MODULE.run_loop(interval_seconds=60, tolerance_seconds=90)

    assert exit_code == 0
    assert sleeps == [60, 60, 60]


def test_run_loop_retries_transient_error_then_recovers(monkeypatch):
    payloads = iter([
        {"status": "error", "stage": "market_session"},
        {"status": "ok"},
        {"status": "skipped", "reason": "outside_alpaca_market_session"},
    ])
    sleeps = []
    monkeypatch.setattr(MODULE, "run_cycle", lambda **_: next(payloads))
    monkeypatch.setattr(MODULE.time, "sleep", lambda seconds: sleeps.append(seconds))

    exit_code = MODULE.run_loop(interval_seconds=60, tolerance_seconds=90)

    assert exit_code == 0
    assert sleeps == [60, 60]
