"""API 路由测试（Mock 外部依赖）。"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.config import settings

API_KEY = settings.API_KEY
HEADERS = {"x-api-key": API_KEY}


@pytest.fixture
def client():
    return TestClient(app)


@patch("src.api.get_health_status")
def test_health(mock_health, client):
    mock_health.return_value = {
        "status": "ok",
        "app": "ColdChain-QA",
        "kb": {"documents": 1, "chunks": 10},
    }
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ask_requires_api_key(client):
    resp = client.post("/api/ask", json={"question": "疫苗运输温度？"})
    assert resp.status_code == 401


@patch("src.api.engine")
def test_ask_success(mock_engine, client):
    mock_engine.ask.return_value = {
        "question": "疫苗运输温度？",
        "answer": "【结论】2-8°C",
        "sources": [],
        "model": "base",
        "latency_ms": 100,
    }
    resp = client.post(
        "/api/ask",
        headers=HEADERS,
        json={"question": "疫苗运输温度？", "model": "base"},
    )
    assert resp.status_code == 200
    assert "2-8°C" in resp.json()["answer"]


@patch("src.api.list_documents")
def test_list_documents(mock_list, client):
    mock_list.return_value = [{"id": 1, "filename": "sample.txt", "chunk_count": 5}]
    resp = client.get("/api/documents", headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["documents"]) == 1


@patch("src.api.delete_document")
@patch("src.api.invalidate_bm25_cache")
def test_delete_document(mock_invalidate, mock_delete, client):
    mock_delete.return_value = True
    resp = client.delete("/api/documents/1", headers=HEADERS)
    assert resp.status_code == 200
    mock_invalidate.assert_called_once()


@patch("src.ingest.vector_store.get_session")
def test_feedback_with_sources(mock_get_session, client):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    resp = client.post(
        "/api/feedback",
        headers=HEADERS,
        json={
            "question": "疫苗温度？",
            "answer": "2-8°C",
            "rating": "good",
            "sources": [{"source": "GSP.pdf", "page": 1}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
