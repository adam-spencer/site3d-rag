import json
from scraper.crawler import Site3DCrawler
from scraper.preprocessor import process_html
from scraper.converter import convert_to_markdown
from scraper.chunker import chunk_markdown

def main():
    base_url = "https://www.site3d.co.uk/help/index.htm"
    # To keep the test reasonable length, we can restrict max_pages. 
    # For a full scale run, this can be increased significantly.
    MAX_PAGES = 1000
    
    print("=== Site3D RAG Pipeline ===")
    
    # 1. Crawl
    crawler = Site3DCrawler(base_url)
    pages = crawler.crawl(max_pages=MAX_PAGES)
    
    all_chunks = []
    parent_docs = {}
    
    
    # 2. Process each page
    for url, html_content in pages.items():
        print(f"Processing: {url}")
        
        # Preprocess
        processed_html, title = process_html(html_content)
        
        # Convert to Markdown
        markdown_text = convert_to_markdown(processed_html)
        
        # Save full document for Parent-Child retrieval
        parent_docs[url] = markdown_text
        
        # Chunk text semantically
        chunks = chunk_markdown(markdown_text, url, title)
        all_chunks.extend(chunks)
        
    print(f"\nProcessing Complete. Generated {len(all_chunks)} semantic chunks.")
    
    # 3. Export to JSONL
    output_filename = "data/chunks.jsonl"
    with open(output_filename, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            record = {
                "page_content": chunk.page_content,
                "metadata": chunk.metadata
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
    print(f"Successfully wrote data to {output_filename}")
    
    # 4. Export Parent Documents mapping to pages.json
    pages_filename = "data/pages.json"
    with open(pages_filename, 'w', encoding='utf-8') as f:
        json.dump(parent_docs, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully wrote parent document maps to {pages_filename}")

if __name__ == "__main__":
    main()
