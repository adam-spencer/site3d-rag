import json
import logging

from api.logging_config import configure_logging
from scraper.crawler import Site3DCrawler
from scraper.preprocessor import process_html
from scraper.converter import convert_to_markdown
from scraper.chunker import chunk_markdown

logger = logging.getLogger(__name__)


def main():
    configure_logging()

    base_url = "https://www.site3d.co.uk/help/index.htm"
    MAX_PAGES = 1000

    logger.info("=== Site3D RAG Pipeline ===")

    crawler = Site3DCrawler(base_url)
    pages = crawler.crawl(max_pages=MAX_PAGES)

    all_chunks = []
    parent_docs = {}

    for url, html_content in pages.items():
        logger.info("Processing: %s", url)

        processed_html, title = process_html(html_content)
        markdown_text = convert_to_markdown(processed_html)
        parent_docs[url] = markdown_text
        chunks = chunk_markdown(markdown_text, url, title)
        all_chunks.extend(chunks)

    logger.info("Processing complete. Generated %d semantic chunks.", len(all_chunks))

    output_filename = "data/chunks.jsonl"
    with open(output_filename, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            record = {"page_content": chunk.page_content, "metadata": chunk.metadata}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Wrote chunks to %s", output_filename)

    pages_filename = "data/pages.json"
    with open(pages_filename, "w", encoding="utf-8") as f:
        json.dump(parent_docs, f, ensure_ascii=False, indent=2)

    logger.info("Wrote parent document map to %s", pages_filename)


if __name__ == "__main__":
    main()
