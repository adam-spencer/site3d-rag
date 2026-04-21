"""Shared fixtures for integration tests.

The key trick: ``create_app(with_lifespan=False)`` skips the FastAPI
lifespan so ChromaDB and Gemini are never touched. Tests then populate
``app.state`` directly with an in-memory fake retriever and LangChain's
built-in ``FakeListChatModel``.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.prompts import ChatPromptTemplate

from api.server import create_app

TEST_PASSWORD = "test-password"


@pytest.fixture(autouse=True)
def _set_app_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PASSWORD", TEST_PASSWORD)


@dataclass
class FakeRetriever:
    """Synchronous stand-in for a LangChain retriever.

    Only ``.invoke`` is exercised by the server; we don't need the full
    Runnable surface here because the retriever is called directly, not
    composed into a pipe.
    """

    docs: list[Document]

    def invoke(self, query: str) -> list[Document]:  # noqa: ARG002
        return self.docs


@pytest.fixture
def fake_retriever() -> FakeRetriever:
    return FakeRetriever(
        docs=[
            Document(
                page_content="Chunk A body.",
                metadata={"source_url": "https://www.site3d.co.uk/help/a.htm"},
            ),
            Document(
                page_content="Chunk B body.",
                metadata={"source_url": "https://www.site3d.co.uk/help/b.htm"},
            ),
        ]
    )


@pytest.fixture
def fake_llm() -> FakeListChatModel:
    # Single-response fake — .astream emits the response one character at a
    # time, which is enough to assert that the NDJSON chunks are flushed.
    return FakeListChatModel(responses=["Hello there!"])


@pytest.fixture
def parent_docs() -> dict[str, str]:
    return {
        "https://www.site3d.co.uk/help/a.htm": "Full page A.",
        "https://www.site3d.co.uk/help/b.htm": "Full page B.",
    }


def _build_app(
    retriever: Any,
    llm: Any,
    parent_docs: dict[str, str],
) -> Any:
    app = create_app(with_lifespan=False)
    app.state.retriever = retriever
    app.state.llm = llm
    app.state.prompt = ChatPromptTemplate.from_template(
        "Context: {context}\nQ: {question}"
    )
    app.state.parent_docs = parent_docs
    return app


@pytest.fixture
def client(
    fake_retriever: FakeRetriever,
    fake_llm: FakeListChatModel,
    parent_docs: dict[str, str],
) -> Iterator[TestClient]:
    app = _build_app(fake_retriever, fake_llm, parent_docs)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_no_retriever(
    fake_llm: FakeListChatModel, parent_docs: dict[str, str]
) -> Iterator[TestClient]:
    app = _build_app(None, fake_llm, parent_docs)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_no_llm(
    fake_retriever: FakeRetriever, parent_docs: dict[str, str]
) -> Iterator[TestClient]:
    app = _build_app(fake_retriever, None, parent_docs)
    with TestClient(app) as c:
        yield c


def iter_ndjson(response_text: str) -> list[dict[str, Any]]:
    """Parse NDJSON response body into a list of records."""
    import json

    return [json.loads(line) for line in response_text.splitlines() if line.strip()]
