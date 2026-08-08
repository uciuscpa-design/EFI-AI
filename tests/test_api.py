from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_paper_trading() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["paper_trading"] is True
