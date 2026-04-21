import asyncio
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from api import vector_store
from api.logging_config import configure_logging

load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """You are an expert engineering assistant for the Site3D software. Use the following context to answer the user's question clearly and accurately.

Each document is labeled with a SOURCE URL.
CRITICAL CITATION RULES:
Whenever you state a fact derived from the provided documents, you MUST warp the relevant phrase or sentence in a standard markdown link pointing to the source URL.
For example: `[The offset distance determines the camera path](https://www.site3d.co.uk/help/forward-visibility.htm)`
DO NOT use traditional bracket numbers like [1]. Let the sentence text itself be the clickable link!
IMPORTANT IMMUNITY: Any images located in the context (formatted as `![alt_text](url)`) MUST NOT be wrapped in a citation link. If you output an image, copy it natively as an image `![alt_text](url)` completely separate from any sentence links.

The context may contain images already formatted as valid Markdown links (e.g. `![alt_text](url)`). When you reference a UI tool, window, or concept that has an image available in the context, you MUST natively copy the exact Markdown image link into your response to show it to the user. Do not modify the URLs.

Context:
{context}

Question: {question}

Answer:"""


class ChatRequest(BaseModel):
    query: str
    password: str = ""


def load_parent_docs(path: str = "data/pages.json") -> dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(
            "Parent documents file %s not found; running in chunks-only mode.", path
        )
        return {}
    except json.JSONDecodeError as e:
        logger.warning(
            "Parent documents file %s is malformed (%s); running in chunks-only mode.",
            path,
            e,
        )
        return {}


def build_retriever() -> Runnable | None:
    try:
        return vector_store.get_retriever()
    except Exception:
        logger.exception("Failed to initialise retriever")
        return None


def build_llm() -> Runnable | None:
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite-preview", temperature=0
        )
    except Exception:
        logger.exception("Failed to initialise Gemini client")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.parent_docs = load_parent_docs()
    app.state.retriever = build_retriever()
    app.state.llm = build_llm()
    app.state.prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    yield


def create_app(*, with_lifespan: bool = True) -> FastAPI:
    """Build the FastAPI app.

    Tests should call ``create_app(with_lifespan=False)`` and populate
    ``app.state`` manually to avoid booting ChromaDB and Gemini.
    """
    app = FastAPI(
        title="Site3D RAG Demo",
        lifespan=lifespan if with_lifespan else None,
    )

    os.makedirs("static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse("static/index.html")

    @app.post("/chat/stream")
    async def chat_stream(
        request: Request, body: ChatRequest
    ) -> StreamingResponse:
        return await _handle_chat_stream(request.app, body)

    return app


def _ndjson_error(message: str, code: str, status: int = 200) -> StreamingResponse:
    async def gen() -> AsyncIterator[str]:
        yield json.dumps({"error": message, "error_code": code}) + "\n"

    return StreamingResponse(
        gen(), media_type="application/x-ndjson", status_code=status
    )


async def _handle_chat_stream(app: FastAPI, body: ChatRequest) -> StreamingResponse:
    expected_password = os.getenv("APP_PASSWORD")
    if not expected_password:
        # Fail closed: no env var = impossible password
        expected_password = secrets.token_hex(32)

    if body.password != expected_password:
        return _ndjson_error(
            "Unauthorized. Invalid or missing password.",
            code="unauthorized",
            status=401,
        )

    retriever: Runnable | None = app.state.retriever
    llm: Runnable | None = app.state.llm
    prompt: ChatPromptTemplate = app.state.prompt
    parent_docs: dict[str, str] = app.state.parent_docs

    if retriever is None:
        return _ndjson_error(
            "Vector store unavailable. Check that data/chroma_db exists.",
            code="retriever_unavailable",
        )
    if llm is None:
        return _ndjson_error(
            "LLM unavailable. Check the GEMINI_API_KEY environment variable.",
            code="llm_unavailable",
        )

    return StreamingResponse(
        _generate_stream(body.query, retriever, llm, prompt, parent_docs),
        media_type="application/x-ndjson",
    )


async def _generate_stream(
    query: str,
    retriever: Runnable,
    llm: Runnable,
    prompt: ChatPromptTemplate,
    parent_docs: dict[str, str],
) -> AsyncIterator[str]:
    try:
        # Pad to flush through ASGI/proxy buffering
        yield json.dumps({"status": "Connecting to engine..."}) + (" " * 2048) + "\n"
        await asyncio.sleep(0.05)

        yield json.dumps({"status": "Retrieving context from ChromaDB..."}) + "\n"
        await asyncio.sleep(0.05)

        # ChromaDB is blocking; offload to thread
        retrieval_start = time.perf_counter()
        docs = await asyncio.to_thread(retriever.invoke, query)
        retrieval_ms = int((time.perf_counter() - retrieval_start) * 1000)

        yield (
            json.dumps(
                {
                    "status": f"Retrieved {len(docs)} documents. Retrieving parent pages..."
                }
            )
            + "\n"
        )
        await asyncio.sleep(0.05)

        # Small-to-big: expand matched chunks to full parent pages
        urls = list(
            dict.fromkeys(
                doc.metadata.get("source_url")
                for doc in docs
                if doc.metadata.get("source_url")
            )
        )

        full_pages = [parent_docs[url] for url in urls if url in parent_docs]

        if not full_pages:
            context_str = "\n\n".join(
                f"DOCUMENT SOURCE URL: {doc.metadata.get('source_url', 'Unknown')}\n{doc.page_content}"
                for doc in docs
            )
        else:
            context_pieces = [
                f"DOCUMENT SOURCE URL: {url}\n{parent_docs[url]}"
                for url in urls
                if url in parent_docs
            ]
            context_str = "\n\n---\n\n".join(context_pieces)

        yield (
            json.dumps(
                {
                    "status": f"Expanded to {len(full_pages)} parent documents. Waiting for Gemini..."
                }
            )
            + "\n"
        )
        await asyncio.sleep(0.05)

        context_str = _inline_images(context_str)

        chain = prompt | llm | StrOutputParser()

        llm_start = time.perf_counter()
        first = True
        async for chunk_text in chain.astream(
            {"context": context_str, "question": query}
        ):
            if first:
                yield (
                    json.dumps({"status": "Generating response...", "clear": True})
                    + "\n"
                )
                first = False
            if chunk_text:
                yield json.dumps({"chunk": chunk_text}) + "\n"
        llm_ms = int((time.perf_counter() - llm_start) * 1000)

        logger.info(
            "query completed retrieval_ms=%d llm_ms=%d chunks=%d parents=%d",
            retrieval_ms,
            llm_ms,
            len(docs),
            len(full_pages),
        )
    except Exception as e:
        logger.exception("Error during stream generation")
        yield json.dumps({"error": str(e), "error_code": "generation_failed"}) + "\n"


def _inline_images(context_str: str) -> str:
    """Replace Markdown image placeholders with HTML <img> tags.

    Done server-side so the LLM cannot mangle the URLs or classes.
    """

    def replace_icon(m: re.Match[str]) -> str:
        alt = m.group(1)
        src = m.group(2)
        url = src if src.startswith("http") else f"https://www.site3d.co.uk/help/{src}"
        return f'<img src="{url}" alt="{alt}" class="inline-icon" />'

    def replace_screenshot(m: re.Match[str]) -> str:
        alt = m.group(1)
        src = m.group(2)
        url = src if src.startswith("http") else f"https://www.site3d.co.uk/help/{src}"
        return f'<img src="{url}" alt="{alt}" class="doc-screenshot" />'

    context_str = re.sub(
        r"\[Screenshot: [^\]]+? - ([^\]]+?)\]\(([^)]+?)\)",
        replace_screenshot,
        context_str,
    )
    context_str = re.sub(
        r"\[Screenshot: ([^\]]+?)\]\(([^)]+?)\)", replace_screenshot, context_str
    )
    context_str = re.sub(
        r"\[Icon: ([^\]]+?)\]\(([^)]+?)\)", replace_icon, context_str
    )
    return context_str


app = create_app()
