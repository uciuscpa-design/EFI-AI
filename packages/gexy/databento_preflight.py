from __future__ import annotations

import importlib.util
import os

from .databento_es import DatabentoEsConfig


def build_databento_preflight() -> dict[str, object]:
    """Inspect local readiness without exposing a key or making a network call."""
    key = (os.getenv("DATABENTO_API_KEY") or "").strip()
    dependency_present = importlib.util.find_spec("databento") is not None
    config = DatabentoEsConfig()

    if not key:
        status = "not_configured"
        next_action = "Provision a Databento API key and set DATABENTO_API_KEY locally; do not commit it."
    elif not dependency_present:
        status = "dependency_missing"
        next_action = "Install the Databento Python client in the local GEXY environment, then run connectivity validation."
    else:
        status = "ready_for_connectivity_test"
        next_action = "Run the read-only Databento connectivity/symbol-mapping check before enabling collection."

    return {
        "status": status,
        "key_present": bool(key),
        "key_length": len(key) if key else 0,
        "key_value_exposed": False,
        "dependency_present": dependency_present,
        "network_attempted": False,
        "planned_subscription": {
            "dataset": config.dataset,
            "schema": config.schema,
            "symbols": [config.continuous_symbol],
            "stype_in": config.stype_in,
        },
        "next_action": next_action,
        "production_feature_enabled": False,
        "production_predictor_changed": False,
        "execution_authorized": False,
    }
