from packages.gexy import databento_preflight


def test_preflight_without_key_is_not_configured_and_never_exposes_value(monkeypatch):
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    monkeypatch.setattr(databento_preflight.importlib.util, "find_spec", lambda _: None)

    report = databento_preflight.build_databento_preflight()

    assert report["status"] == "not_configured"
    assert report["key_present"] is False
    assert report["key_length"] == 0
    assert report["key_value_exposed"] is False
    assert report["network_attempted"] is False
    assert report["production_feature_enabled"] is False
    assert report["production_predictor_changed"] is False
    assert report["execution_authorized"] is False


def test_preflight_with_key_but_without_dependency_reports_dependency_missing(monkeypatch):
    monkeypatch.setenv("DATABENTO_API_KEY", "secret-test-key")
    monkeypatch.setattr(databento_preflight.importlib.util, "find_spec", lambda _: None)

    report = databento_preflight.build_databento_preflight()

    assert report["status"] == "dependency_missing"
    assert report["key_present"] is True
    assert report["key_length"] == len("secret-test-key")
    assert "secret-test-key" not in str(report)
    assert report["key_value_exposed"] is False
    assert report["network_attempted"] is False


def test_preflight_ready_state_preserves_frozen_read_only_subscription(monkeypatch):
    monkeypatch.setenv("DATABENTO_API_KEY", "secret-test-key")
    monkeypatch.setattr(databento_preflight.importlib.util, "find_spec", lambda _: object())

    report = databento_preflight.build_databento_preflight()

    assert report["status"] == "ready_for_connectivity_test"
    assert report["planned_subscription"] == {
        "dataset": "GLBX.MDP3",
        "schema": "trades",
        "symbols": ["ES.v.0"],
        "stype_in": "continuous",
    }
    assert report["network_attempted"] is False
    assert report["execution_authorized"] is False
