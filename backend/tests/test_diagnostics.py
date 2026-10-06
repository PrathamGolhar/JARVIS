from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_diagnostics_endpoint_returns_real_subsystems() -> None:
    response = client.get("/api/diagnostics")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "systemMetrics" in data
    assert len(data["items"]) >= 5

    item_ids = [item["id"] for item in data["items"]]
    assert "ai_engine" in item_ids
    assert "network" in item_ids
    assert "tts" in item_ids
    assert "systemmetrics" in str(data).lower()
