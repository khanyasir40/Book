from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_details_endpoint_handles_invalid_id():
    resp = client.get("/api/books/invalid-id-123")
    assert resp.status_code in (404, 200)
    if resp.status_code == 200:
        data = resp.json()
        assert "id" in data
        assert "title" in data