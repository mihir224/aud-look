from fastapi.testclient import TestClient

import app.api as api
from app.schemas import SearchResponse


def test_search_api_rejects_unknown_strategy():
    client = TestClient(api.app)
    response = client.get("/api/v1/search", params={"q": "money", "strategy": "unknown"})
    assert response.status_code == 422


def test_search_api_delegates_to_retrieval(monkeypatch):
    expected = SearchResponse(query="money", strategy="hybrid", results=[], elapsed_ms=1)
    monkeypatch.setattr(api, "search", lambda *_, **__: expected)
    client = TestClient(api.app)
    response = client.get("/api/v1/search", params={"q": "money"})
    assert response.status_code == 200
    assert response.json()["query"] == "money"
