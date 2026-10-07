from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/api/health")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    # Accept additional metadata fields (system, version) in the liveness response
    assert "system" not in data or data["system"] == "JARVIS 2.0"
