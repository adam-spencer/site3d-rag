"""Happy-path streaming behaviour for /chat/stream."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD, iter_ndjson


def _post(client: TestClient, query: str = "how do alignments work?"):
    return client.post(
        "/chat/stream", json={"query": query, "password": TEST_PASSWORD}
    )


def test_stream_returns_200_and_ndjson_content_type(client: TestClient):
    r = _post(client)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")


def test_stream_emits_status_updates_and_chunks_in_order(client: TestClient):
    r = _post(client)
    records = iter_ndjson(r.text)

    # Expected ordered sequence of status messages
    statuses = [r["status"] for r in records if "status" in r]
    assert any(s.startswith("Connecting to engine") for s in statuses)
    assert any(s.startswith("Retrieving context") for s in statuses)
    assert any("Retrieved" in s and "parent pages" in s for s in statuses)
    assert any("Expanded to" in s for s in statuses)
    assert any(s.startswith("Generating response") for s in statuses)

    # At least one chunk of generated text came through
    chunks = [r["chunk"] for r in records if "chunk" in r]
    assert chunks, f"expected at least one chunk, got: {records}"
    assert "".join(chunks) == "Hello there!"


def test_stream_reports_retrieved_and_parent_document_counts(client: TestClient):
    r = _post(client)
    records = iter_ndjson(r.text)
    statuses = [r["status"] for r in records if "status" in r]

    # The fake retriever returns 2 docs; both sources are in parent_docs
    assert any("Retrieved 2 documents" in s for s in statuses)
    assert any("Expanded to 2 parent documents" in s for s in statuses)


def test_generating_status_has_clear_flag(client: TestClient):
    r = _post(client)
    records = iter_ndjson(r.text)
    generating = [r for r in records if r.get("status", "").startswith("Generating")]
    assert generating
    assert generating[0].get("clear") is True
