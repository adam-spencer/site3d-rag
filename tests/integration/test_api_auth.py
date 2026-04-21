"""Authentication and degraded-mode error paths for /chat/stream."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD, iter_ndjson


def test_wrong_password_returns_401_ndjson(client: TestClient):
    r = client.post(
        "/chat/stream", json={"query": "anything", "password": "nope"}
    )
    assert r.status_code == 401
    records = iter_ndjson(r.text)
    assert len(records) == 1
    assert records[0]["error_code"] == "unauthorized"
    assert "Unauthorized" in records[0]["error"]


def test_missing_password_returns_401(client: TestClient):
    r = client.post("/chat/stream", json={"query": "anything"})
    assert r.status_code == 401
    records = iter_ndjson(r.text)
    assert records[0]["error_code"] == "unauthorized"


def test_missing_app_password_env_fails_closed(
    client: TestClient, monkeypatch
):
    # Strip the env var set by the autouse fixture; auth must then fail
    # closed even for an empty password submission.
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    r = client.post(
        "/chat/stream", json={"query": "anything", "password": TEST_PASSWORD}
    )
    assert r.status_code == 401


def test_retriever_unavailable_returns_error_code(
    client_no_retriever: TestClient,
):
    r = client_no_retriever.post(
        "/chat/stream", json={"query": "anything", "password": TEST_PASSWORD}
    )
    records = iter_ndjson(r.text)
    assert len(records) == 1
    assert records[0]["error_code"] == "retriever_unavailable"


def test_llm_unavailable_returns_error_code(client_no_llm: TestClient):
    r = client_no_llm.post(
        "/chat/stream", json={"query": "anything", "password": TEST_PASSWORD}
    )
    records = iter_ndjson(r.text)
    assert len(records) == 1
    assert records[0]["error_code"] == "llm_unavailable"
