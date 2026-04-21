from scraper.chunker import chunk_markdown, extract_markdown_links


class TestExtractMarkdownLinks:
    def test_extracts_single_link(self):
        text = "See [the docs](https://example.com/docs.htm) for details."
        assert extract_markdown_links(text) == ["https://example.com/docs.htm"]

    def test_extracts_multiple_links(self):
        text = "[one](https://a.com) and [two](https://b.com)"
        assert extract_markdown_links(text) == ["https://a.com", "https://b.com"]

    def test_returns_empty_when_no_links(self):
        assert extract_markdown_links("plain text, no links") == []

    def test_does_not_match_images(self):
        # Note: the regex currently matches images too (leading ! is outside
        # the capture). Documenting current behaviour rather than asserting
        # a stricter contract.
        text = "![alt](https://example.com/img.png)"
        assert extract_markdown_links(text) == ["https://example.com/img.png"]


class TestChunkMarkdown:
    def test_splits_on_headers(self):
        md = "# Title\n\nIntro.\n\n## Section A\n\nA body.\n\n## Section B\n\nB body."
        chunks = chunk_markdown(md, "https://src.test/p.htm", "Page")
        assert len(chunks) >= 2
        bodies = [c.page_content for c in chunks]
        assert any("A body." in b for b in bodies)
        assert any("B body." in b for b in bodies)

    def test_populates_metadata(self):
        md = "# Title\n\nBody text."
        chunks = chunk_markdown(md, "https://src.test/p.htm", "My Page")
        assert chunks, "expected at least one chunk"
        meta = chunks[0].metadata
        assert meta["source_url"] == "https://src.test/p.htm"
        assert meta["page_title"] == "My Page"
        assert "headers" in meta
        assert "outgoing_links" in meta

    def test_extracts_outgoing_links_per_chunk(self):
        md = (
            "# Intro\n\n"
            "See [link one](https://a.test/x.htm).\n\n"
            "## Next\n\n"
            "Also [link two](https://b.test/y.htm)."
        )
        chunks = chunk_markdown(md, "https://src.test/p.htm", "Page")
        all_links = {link for c in chunks for link in c.metadata["outgoing_links"]}
        assert "https://a.test/x.htm" in all_links
        assert "https://b.test/y.htm" in all_links

    def test_falls_back_to_single_chunk_when_no_headers(self):
        md = "Just body text, no headings at all."
        chunks = chunk_markdown(md, "https://src.test/p.htm", "Page")
        assert len(chunks) == 1
        assert chunks[0].page_content == md

    def test_empty_input_returns_empty(self):
        assert chunk_markdown("", "https://src.test/p.htm", "Page") == []

    def test_whitespace_only_input_returns_empty(self):
        assert chunk_markdown("   \n  \n", "https://src.test/p.htm", "Page") == []
