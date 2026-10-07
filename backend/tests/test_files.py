import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_file_upload_and_extraction() -> None:
    file_content = b"JARVIS Architecture Document\nVersion 1.0\nStatus: Production"
    response = client.post(
        "/api/files/upload",
        files={"file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["filename"] == "test_doc.txt"
    assert data["fileType"] == "txt"
    assert "JARVIS Architecture" in data["extractedTextPreview"]


def test_file_upload_rejects_empty_file() -> None:
    response = client.post(
        "/api/files/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 422


def test_file_download_path_traversal_protection() -> None:
    # Attempt path traversal
    response = client.get("/api/files/download/../../../../etc/passwd")
    assert response.status_code in (400, 404)

    response = client.delete("/api/files/../../../../etc/passwd")
    assert response.status_code in (400, 404)

