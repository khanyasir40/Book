from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_search_invalid_min_rating():
    resp = client.get("/api/books/search", params={"min_rating": 6})
    assert resp.status_code == 422