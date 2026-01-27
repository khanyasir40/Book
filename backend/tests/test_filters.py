from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_search_with_filters_returns_scored_books():
    resp = client.get("/api/books/search", params={
        "query": "python",
        "author": "Guido",
        "genre": "Programming",
        "language": "en",
        "min_rating": 0,
        "max_results": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        b = data[0]
        assert "score" in b
        assert "confidence_pct" in b
        assert "title" in b