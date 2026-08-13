import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_live_predict.py"
SPEC = importlib.util.spec_from_file_location("gexy_live_predict", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_paper_key_shape_rejects_non_pk(monkeypatch):
    monkeypatch.setenv("APCA_API_KEY_ID", "YO1234567890")
    assert MODULE._paper_key_shape_is_plausible() is False


def test_paper_key_shape_accepts_plausible_pk(monkeypatch):
    monkeypatch.setenv("APCA_API_KEY_ID", "PK123456789012345678")
    assert MODULE._paper_key_shape_is_plausible() is True
    meta = MODULE._credential_meta()
    assert meta["key_prefix"] == "PK"
    assert meta["key_length"] == 20
