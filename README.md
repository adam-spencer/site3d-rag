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

2.  **Create a virtual environment** and install dependencies:
    ```bash
    uv venv
    uv pip install -r requirements.txt
    ```

3.  **Set up environment variables**:
    Create a `.env` file in the root directory with the following content:
    ```env
    GEMINI_API_KEY="your-gemini-api-key-here"
    ```

## Usage

1.  **Start the server**:
    ```bash
    uv run uvicorn api.server:app --reload
    ```

2.  **Access the UI**:
    Open your browser and navigate to `http://localhost:8000`.

## Project Structure

- `api/`: Contains the FastAPI server and vector store logic.
  - `server.py`: The main FastAPI application.
  - `vector_store.py`: Handles ChromaDB initialization and retrieval.
- `data/`: Stores the ChromaDB database files.
- `docs/`: Contains the documentation content used for indexing.
- `static/`: Frontend HTML, CSS, and JavaScript.
  - `index.html`: The chat interface.
  - `style.css`: Styles for the interface.
  - `script.js`: Client-side logic for the chat.
- `requirements.txt`: Project dependencies.
- `.env`: Environment variables (should not be committed to version control).
