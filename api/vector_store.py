import atexit
import json
import logging
import os
import shutil
import tempfile
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


def load_chunks(file_path: str = "data/chunks.jsonl") -> list[Document]:
    documents: list[Document] = []
    if not os.path.exists(file_path):
        return documents

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            # Flatten nested metadata for Chroma compatibility
            metadata = data.get("metadata", {})
            flat_meta: dict[str, Any] = {}
            for k, v in metadata.items():
                if isinstance(v, (dict, list)):
                    flat_meta[k] = json.dumps(v)
                else:
                    flat_meta[k] = v

            text = data.get("page_content", "")
            if text:
                documents.append(Document(page_content=text, metadata=flat_meta))
    return documents


def get_vector_store() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    persist_directory = "./data/chroma_db"

    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        # Chroma opens SQLite read-write even for queries, which mutates
        # the underlying file. Copy to a temp dir so the committed DB
        # stays byte-identical across runs.
        temp_dir = tempfile.mkdtemp(prefix="site3d_chroma_")
        logger.info(
            "Copying Chroma database from %s to %s (read-only source)",
            persist_directory,
            temp_dir,
        )
        shutil.copytree(persist_directory, temp_dir, dirs_exist_ok=True)
        atexit.register(shutil.rmtree, temp_dir, ignore_errors=True)
        db = Chroma(persist_directory=temp_dir, embedding_function=embeddings)
    else:
        logger.info("Creating new Chroma database from chunks")
        docs = load_chunks()
        if not docs:
            raise RuntimeError(
                "No chunks found. Run 'python -m scraper' to generate data/chunks.jsonl."
            )
        db = Chroma.from_documents(
            documents=docs, embedding=embeddings, persist_directory=persist_directory
        )
        logger.info("Created vector store with %d documents", len(docs))

    return db


def get_retriever() -> Runnable[str, list[Document]]:
    db = get_vector_store()
    return db.as_retriever(search_kwargs={"k": 5})


if __name__ == "__main__":
    get_vector_store()
