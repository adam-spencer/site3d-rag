import json

from api.vector_store import load_chunks


def test_load_chunks_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "nope.jsonl"
    assert load_chunks(str(missing)) == []


def test_load_chunks_reads_page_content_and_metadata(tmp_path):
    jsonl = tmp_path / "chunks.jsonl"
    records = [
        {
            "page_content": "Hello world.",
            "metadata": {"source_url": "https://a.test/p.htm", "page_title": "P"},
        },
        {
            "page_content": "Second chunk.",
            "metadata": {"source_url": "https://a.test/q.htm", "page_title": "Q"},
        },
    ]
    jsonl.write_text("\n".join(json.dumps(r) for r in records) + "\n")

    docs = load_chunks(str(jsonl))
    assert len(docs) == 2
    assert docs[0].page_content == "Hello world."
    assert docs[0].metadata["source_url"] == "https://a.test/p.htm"
    assert docs[1].metadata["page_title"] == "Q"


def test_load_chunks_flattens_nested_metadata(tmp_path):
    jsonl = tmp_path / "chunks.jsonl"
    record = {
        "page_content": "Body",
        "metadata": {
            "source_url": "https://a.test/p.htm",
            "headers": {"H1": "Title"},
            "outgoing_links": ["https://b.test"],
        },
    }
    jsonl.write_text(json.dumps(record) + "\n")

    docs = load_chunks(str(jsonl))
    assert len(docs) == 1
    # Chroma can't store nested values — these must be JSON-encoded strings
    assert docs[0].metadata["headers"] == json.dumps({"H1": "Title"})
    assert docs[0].metadata["outgoing_links"] == json.dumps(["https://b.test"])


def test_load_chunks_skips_blank_lines(tmp_path):
    jsonl = tmp_path / "chunks.jsonl"
    record = {"page_content": "Body", "metadata": {}}
    jsonl.write_text(f"\n{json.dumps(record)}\n\n")
    docs = load_chunks(str(jsonl))
    assert len(docs) == 1


def test_load_chunks_skips_records_without_page_content(tmp_path):
    jsonl = tmp_path / "chunks.jsonl"
    records = [
        {"page_content": "", "metadata": {}},
        {"page_content": "real", "metadata": {}},
    ]
    jsonl.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    docs = load_chunks(str(jsonl))
    assert len(docs) == 1
    assert docs[0].page_content == "real"
