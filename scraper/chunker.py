import re
from typing import List
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document


def extract_markdown_links(markdown_text: str) -> List[str]:
    """Extract all URLs from markdown formatted links [text](url)."""
    # Simple regex for markdown links: [text](link)
    # The URL is capturing group 1
    # Example matches: [Link](http://example.com), [img](../abc.png)
    # NOTE: To be safe with spaces in links we use a non-greedy match inside the parens
    pattern = r"\[.*?\]\((.*?)\)"
    links = re.findall(pattern, markdown_text)
    return links


def chunk_markdown(
    markdown_text: str, source_url: str, page_title: str
) -> List[Document]:
    """Chunk the markdown semantically and enrich with metadata."""
    headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,  # Keep headers in the chunk content for semantic completeness
    )

    chunks = markdown_splitter.split_text(markdown_text)

    # If the text has no headers, it might return empty or without metadata headers; handle graceful fallbacks
    if not chunks and markdown_text.strip():
        chunks = [Document(page_content=markdown_text, metadata={})]

    for chunk in chunks:
        outgoing_links = extract_markdown_links(chunk.page_content)

        # Original metadata from markdown_splitter looks like {"H1": "Header Title", "H2": "Sub Title"}
        headers = chunk.metadata.copy()

        # Re-assign enriched metadata
        chunk.metadata = {
            "source_url": source_url,
            "page_title": page_title,
            "headers": headers,
            "outgoing_links": outgoing_links,
        }

    return chunks
