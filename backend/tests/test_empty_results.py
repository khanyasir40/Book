from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_search_empty_or_nonempty_is_handled():
    resp = client.get("/api/books/search", params={
        "query": "zzzzzzzzzzzzzzzzzzzzzz",
        "min_rating": 5,
        "max_results": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)