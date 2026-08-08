from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import require_api_key
from packages.core.config import Settings


def test_api_key_dependency_allows_unconfigured_mode(monkeypatch) -> None:
    monkeypatch.setattr("apps.api.dependencies.get_settings", lambda: Settings(api_key=""))
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_api_key)])
    def protected() -> dict[str, bool]:
        return {"ok": True}

    assert TestClient(app).get("/protected").status_code == 200


def test_api_key_dependency_rejects_invalid_key(monkeypatch) -> None:
    monkeypatch.setattr("apps.api.dependencies.get_settings", lambda: Settings(api_key="expected"))
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_api_key)])
    def protected() -> dict[str, bool]:
        return {"ok": True}

    assert TestClient(app).get("/protected", headers={"x-api-key": "wrong"}).status_code == 401
