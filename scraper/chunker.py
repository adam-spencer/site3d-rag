import re
from typing import List
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document


def extract_markdown_links(markdown_text: str) -> List[str]:
    """Extract URLs from markdown links."""
    pattern = r"\[.*?\]\((.*?)\)"
    links = re.findall(pattern, markdown_text)
    return links


def chunk_markdown(
    markdown_text: str, source_url: str, page_title: str
) -> List[Document]:
    """Split markdown by headers and enrich with metadata."""
    headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    chunks = markdown_splitter.split_text(markdown_text)

    if not chunks and markdown_text.strip():
        chunks = [Document(page_content=markdown_text, metadata={})]

    for chunk in chunks:
        outgoing_links = extract_markdown_links(chunk.page_content)
        headers = chunk.metadata.copy()
        chunk.metadata = {
            "source_url": source_url,
            "page_title": page_title,
            "headers": headers,
            "outgoing_links": outgoing_links,
        }

    return chunks
