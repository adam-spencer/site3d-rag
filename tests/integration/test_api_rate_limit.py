"""Rate limiting on /chat/stream."""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.prompts import ChatPromptTemplate

from api.server import create_app
from tests.conftest import TEST_PASSWORD, FakeRetriever, iter_ndjson


@pytest.fixture
def rate_limited_client(
    fake_retriever: FakeRetriever,
    fake_llm: FakeListChatModel,
    parent_docs: dict[str, str],
) -> Iterator[TestClient]:
    app = create_app(with_lifespan=False, rate_limit="2/minute")
    app.state.retriever = fake_retriever
    app.state.llm = fake_llm
    app.state.prompt = ChatPromptTemplate.from_template(
        "Context: {context}\nQ: {question}"
    )
    app.state.parent_docs = parent_docs
    with TestClient(app) as c:
        yield c


def test_over_limit_requests_return_429_ndjson(rate_limited_client: TestClient):
    payload = {"query": "hi", "password": TEST_PASSWORD}

    # First two should succeed
    assert rate_limited_client.post("/chat/stream", json=payload).status_code == 200
    assert rate_limited_client.post("/chat/stream", json=payload).status_code == 200

    # Third should be rate-limited
    r3 = rate_limited_client.post("/chat/stream", json=payload)
    assert r3.status_code == 429
    records = iter_ndjson(r3.text)
    assert records[0]["error_code"] == "rate_limited"


def test_forwarded_for_is_honoured(
    fake_retriever: FakeRetriever,
    fake_llm: FakeListChatModel,
    parent_docs: dict[str, str],
):
    """Requests from different X-Forwarded-For addresses have independent buckets."""
    app = create_app(with_lifespan=False, rate_limit="1/minute")
    app.state.retriever = fake_retriever
    app.state.llm = fake_llm
    app.state.prompt = ChatPromptTemplate.from_template("x")
    app.state.parent_docs = parent_docs

    with TestClient(app) as client:
        payload = {"query": "hi", "password": TEST_PASSWORD}

        # First call from client A succeeds
        r1 = client.post(
            "/chat/stream", json=payload, headers={"x-forwarded-for": "1.2.3.4"}
        )
        assert r1.status_code == 200

        # Second call from the same IP is throttled
        r2 = client.post(
            "/chat/stream", json=payload, headers={"x-forwarded-for": "1.2.3.4"}
        )
        assert r2.status_code == 429

        # But a call from a different IP goes through
        r3 = client.post(
            "/chat/stream", json=payload, headers={"x-forwarded-for": "5.6.7.8"}
        )
        assert r3.status_code == 200
