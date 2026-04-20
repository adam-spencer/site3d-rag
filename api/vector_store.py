import json
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


def load_chunks(file_path: str = "data/chunks.jsonl") -> list:
    documents = []
    if not os.path.exists(file_path):
        return documents

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            # Flatten nested metadata for Chroma compatibility
            metadata = data.get("metadata", {})
            flat_meta = {}
            for k, v in metadata.items():
                if isinstance(v, (dict, list)):
                    flat_meta[k] = json.dumps(v)
                else:
                    flat_meta[k] = v

            text = data.get("page_content", "")
            if text:
                documents.append(Document(page_content=text, metadata=flat_meta))
    return documents


def get_vector_store():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    persist_directory = "./data/chroma_db"

    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        print("Loading existing Chroma database...")
        db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    else:
        print("Creating new Chroma database from chunks...")
        docs = load_chunks()
        if not docs:
            raise Exception(
                "No chunks found. Have you run run_scrape.py to generate data/chunks.jsonl?"
            )
        db = Chroma.from_documents(
            documents=docs, embedding=embeddings, persist_directory=persist_directory
        )
        print(f"Created Vector Store with {len(docs)} documents.")

    return db


def get_retriever():
    db = get_vector_store()
    return db.as_retriever(search_kwargs={"k": 5})


if __name__ == "__main__":
    get_vector_store()
