---
title: Site3D RAG
emoji: 🏗️
colorFrom: yellow
colorTo: orange
sdk: docker
app_port: 8000
pinned: false
---

# Site3D RAG System

This project implements a Retrieval-Augmented Generation (RAG) system for the Site3D software documentation. It uses a local vector database (ChromaDB) and Google's Gemini API to provide intelligent answers to user queries based on the documentation content.

## Features

- **RAG Architecture**: Retrieves relevant documentation chunks to provide context to the LLM.
- **ChromaDB**: Uses a local vector store for efficient similarity search.
- **Gemini 3.1 Flash Lite**: Powered by Google's latest Gemini model.
- **Streaming Responses**: Real-time streaming of LLM responses for a better user experience.
- **Markdown Image Support**: Automatically formats and displays images from the documentation.

## Prerequisites

- Python 3.8+
- `uv` (for dependency management)
- Google Gemini API Key

## Installation

1.  **Clone the repository** (if not already done).

2.  **Install dependencies**:
    ```bash
    uv sync
    ```

3.  **Set up environment variables**:
    Create a `.env` file in the root directory with the following content:
    ```env
    GEMINI_API_KEY="your-gemini-api-key-here"
    ```

## Usage

1.  **Generate the Document Database**:
    If this is your first time checking out the repository, run the scraper to recursively pull and chunk the Site3D engineering documentation direct from the web.
    ```bash
    uv run run_scrape.py
    ```

2.  **Start the server**:
    ```bash
    uv run uvicorn api.server:app
    ```

3.  **Access the UI**:
    Open your browser and navigate to `http://localhost:8000`.

## Project Structure

- `api/`: Contains the FastAPI server and vector store logic.
  - `server.py`: The main FastAPI application.
  - `vector_store.py`: Handles ChromaDB initialization and embedding generation.
- `scraper/`: The documentation ingestion pipeline.
  - `crawler.py`: Recursive web crawler respecting anti-scraping blockers.
  - `preprocessor.py`: Transforms raw HTML DOM trees and handles Image placeholder links.
  - `converter.py`: Transforms HTML layouts into clean Markdown formatting.
  - `chunker.py`: Semantically chunks Markdown along header breaks for embedding context.
- `data/`: Stores the ChromaDB database and physical chunk outputs (generated locally).
- `static/`: Frontend HTML, CSS, and JavaScript.
  - `index.html`: The chat interface UI.
  - `style.css`: Styles for the interface.
  - `script.js`: Reactive text streaming rendering loop.
- `run_scrape.py`: CLI execution script for the data ingestion pipeline.
- `pyproject.toml` & `uv.lock`: Project dependencies and configuration.
- `.env`: API environment variable targets (ignored by tracking).
