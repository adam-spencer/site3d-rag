# Site3D RAG System

A Retrieval-Augmented Generation (RAG) assistant for searching the [Site3D software](https://www.site3d.co.uk/) engineering documentation through natural language queries.
Built with a **FastAPI** backend, **LangChain** for orchestration, **ChromaDB** for vector storage, and Google's **Gemini API** for generation. The frontend streams responses in real-time via NDJSON over HTTP.

<div align="center">
  <video src="https://github.com/user-attachments/assets/24dfe037-4bb3-4abe-841b-87debcf5803c" autoplay loop muted playsinline></video>
</div>

The project is containerised with **Docker** for deployment to cloud platforms. A live instance is hosted on [HuggingFace Spaces](https://huggingface.co/spaces/adam-spencer/site3d-rag). Please contact me directly for access.

## Core Tech & Features

- **LangChain Orchestration**: Manages the RAG pipeline, from retrieving documents and assembling context through to streaming responses from Gemini.
- **Streaming Responses**: The backend uses FastAPI's `StreamingResponse` to push NDJSON chunks to the frontend, which parses and renders them incrementally as they arrive.
- **Containerised Deployment**: Fully packaged in Docker for deployment to platforms like HuggingFace Spaces.
- **Small-to-Big Retrieval**: ChromaDB identifies the most relevant chunks, then the server expands each match to its full parent page via a prebuilt lookup map (`pages.json`), giving Gemini complete surrounding context before answering.
- **Fail-Closed Authentication**: The backend rejects any request that doesn't include the correct password (set via environment variable). If the environment variable is missing entirely, a cryptographically random password is generated at startup, making access impossible by default.
- **Per-IP Rate Limiting**: `slowapi` throttles `/chat/stream` (default `10/minute`, overridable via `CHAT_RATE_LIMIT`). A custom key function reads the first entry of `X-Forwarded-For` so limits behave correctly behind the HuggingFace Spaces proxy. 429 responses are emitted as NDJSON with an `error_code` so the frontend handles them through the same parser as other streaming errors.
- **Structured Logging & Timings**: All components use the `logging` module through a shared configuration; each query emits a single `INFO` line with retrieval and generation timings (e.g. `retrieval_ms=230 llm_ms=1840 chunks=5 parents=3`). Log level is controllable via `LOG_LEVEL`.
- **Strict Type Checking**: Full type hints across `api/` and `scraper/`; `mypy --strict` runs clean on every pull request alongside `ruff` and the test suite.
- **Inline Source Citations**: The prompt instructs Gemini to embed source URLs as inline markdown links. The frontend CSS renders these as highlighted, clickable spans within the response text.
- **Image Path Correction**: LLMs occasionally drop path segments from URLs. The frontend applies a regex to detect broken documentation image paths and re-insert the missing `/images/` directory before rendering.
- **ChromaDB & Gemini**: Uses ChromaDB with HuggingFace `all-MiniLM-L6-v2` embeddings for local vector search, and Gemini 2.0 Flash Lite (Preview) for generation.

## Data Ingestion & Web Scraping

The ingestion pipeline uses `requests` and `BeautifulSoup4` for crawling and DOM manipulation, with `markdownify` handling the HTML-to-Markdown conversion:

1. **Recursive Web Crawler** (`crawler.py`): Starts at the documentation index and follows internal links to discover and download all `.htm` pages. Applies a 1-second delay between requests and uses browser-style headers to crawl politely.
2. **DOM Preprocessing** (`preprocessor.py`): Before conversion, replaces `<img>` tags with structured Markdown placeholders, classifying each image as either an inline UI icon or a documentation screenshot based on filename keywords and dimension attributes.
3. **Markdown Conversion** (`converter.py`): Passes the preprocessed HTML through `markdownify`, which strips non-content elements (`<script>`, `<style>`, `<nav>`, `<footer>`, `<iframe>`) and converts the remaining DOM to clean ATX-style Markdown.
4. **Semantic Chunking** (`chunker.py`): Splits the Markdown along header boundaries (`H1`, `H2`, `H3`) using LangChain's `MarkdownHeaderTextSplitter`, ensuring each chunk represents a structurally complete section rather than an arbitrary character-count slice.

## Testing & CI

51 tests cover the scraper pipeline, API auth, streaming, and rate limiting. The whole suite runs in ~3 seconds with no network, no model weights, and no ChromaDB.

- **Offline scraper tests**: The crawler is tested against the `responses` library, which mocks out `requests` at the transport layer. Crawl-follow, `max_pages` caps, fragment deduplication, and HTTP-error recovery are all covered deterministically.
- **Offline API tests**: A factory (`create_app(with_lifespan=False)`) skips the FastAPI lifespan entirely, so tests inject a fake retriever and LangChain's built-in `FakeListChatModel` directly onto `app.state`. ChromaDB and Gemini are never touched at test time.
- **Rate-limit tests**: Each app builds its own `Limiter`, giving every test isolated counters and allowing the 429 path and `X-Forwarded-For` bucketing to be asserted in isolation.
- **GitHub Actions**: Every push and pull request runs `ruff check`, `mypy api scraper`, and `pytest` via `.github/workflows/ci.yml`.

## Prerequisites

- Python 3.10+
- `uv` (for dependency management)
- Google Gemini API Key

## Installation

1.  **Clone the repository** (if not already done).

2.  **Install dependencies**:
    ```bash
    uv sync              # runtime only
    uv sync --group dev  # runtime + pytest, mypy, ruff, etc.
    ```

3.  **Set up environment variables**:
    Create a `.env` file in the root directory with the following content:
    ```env
    GEMINI_API_KEY="your-gemini-api-key-here"
    APP_PASSWORD="your-secure-password"
    # Optional:
    # LOG_LEVEL="INFO"           # DEBUG / INFO / WARNING / ERROR
    # CHAT_RATE_LIMIT="10/minute"
    ```

## Usage

1.  **Generate the Document Database**:
    If this is your first time checking out the repository, run the scraper to crawl and chunk the Site3D documentation.
    ```bash
    uv run python -m scraper
    ```

2.  **Start the server**:
    ```bash
    uv run uvicorn api.server:app
    ```

3.  **Access the UI**:
    Open your browser and navigate to `http://localhost:8000`.

## Project Structure

- `api/`: FastAPI server and vector store logic.
  - `server.py`: Main application. Handles authentication, rate limiting, small-to-big context expansion, prompt construction, and streamed response generation. `create_app()` is a factory so tests can build the app with the lifespan skipped.
  - `vector_store.py`: Loads chunks from JSONL, initialises ChromaDB with HuggingFace embeddings, and exposes a LangChain retriever.
  - `logging_config.py`: Shared logging setup used by both the server and the scraper entry point.
- `scraper/`: Documentation ingestion pipeline.
  - `crawler.py`: Recursive web crawler with rate limiting and link validation.
  - `preprocessor.py`: Replaces `<img>` elements with classified Markdown placeholders (icons vs screenshots).
  - `converter.py`: Thin wrapper around `markdownify` for HTML-to-Markdown conversion.
  - `chunker.py`: Splits Markdown along header boundaries and enriches chunks with source metadata.
  - `__main__.py`: Entry point for the data ingestion pipeline (`python -m scraper`).
- `tests/`: Unit tests for the scraper modules and integration tests for the API. Run with `uv run pytest`.
- `data/`: Stores the ChromaDB database and intermediate pipeline outputs (generated locally, not checked in).
- `static/`: Frontend HTML, CSS, and JavaScript.
  - `index.html`: Chat interface with a password authentication overlay.
  - `style.css`: Dark-mode glassmorphic design system with inline icon alignment and citation styling.
  - `script.js`: NDJSON stream reader, incremental Markdown rendering, image path correction, and link delegation.
- `.github/workflows/`: `ci.yml` (lint + mypy + pytest on every push and PR) and `hf_sync.yml` (push-to-main deploy to HuggingFace Spaces).
- `pyproject.toml` & `uv.lock`: Project dependencies and configuration (including `[dependency-groups.dev]`, `[tool.pytest.ini_options]`, and `[tool.mypy]`).
- `Dockerfile`: Container configuration for HuggingFace Spaces deployment (binds to `0.0.0.0:8000`).
- `.env`: Environment variables for API keys and authentication (not tracked in git).
