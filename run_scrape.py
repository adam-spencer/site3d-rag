import json
from scraper.crawler import Site3DCrawler
from scraper.preprocessor import process_html
from scraper.converter import convert_to_markdown
from scraper.chunker import chunk_markdown


def main():
    base_url = "https://www.site3d.co.uk/help/index.htm"
    MAX_PAGES = 1000

    print("=== Site3D RAG Pipeline ===")

    crawler = Site3DCrawler(base_url)
    pages = crawler.crawl(max_pages=MAX_PAGES)

    all_chunks = []
    parent_docs = {}

    for url, html_content in pages.items():
        print(f"Processing: {url}")

        processed_html, title = process_html(html_content)
        markdown_text = convert_to_markdown(processed_html)
        parent_docs[url] = markdown_text
        chunks = chunk_markdown(markdown_text, url, title)
        all_chunks.extend(chunks)

    print(f"\nProcessing Complete. Generated {len(all_chunks)} semantic chunks.")

    output_filename = "data/chunks.jsonl"
    with open(output_filename, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            record = {"page_content": chunk.page_content, "metadata": chunk.metadata}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Successfully wrote data to {output_filename}")

    pages_filename = "data/pages.json"
    with open(pages_filename, "w", encoding="utf-8") as f:
        json.dump(parent_docs, f, ensure_ascii=False, indent=2)

    print(f"Successfully wrote parent document maps to {pages_filename}")


if __name__ == "__main__":
    main()
