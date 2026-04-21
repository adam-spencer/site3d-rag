import responses

from scraper.crawler import Site3DCrawler


class TestIsValidLink:
    def setup_method(self):
        self.crawler = Site3DCrawler("https://www.site3d.co.uk/help/index.htm")

    def test_accepts_help_htm(self):
        assert self.crawler._is_valid_link(
            "https://www.site3d.co.uk/help/alignments.htm"
        )

    def test_accepts_help_html(self):
        assert self.crawler._is_valid_link(
            "https://www.site3d.co.uk/help/alignments.html"
        )

    def test_rejects_external_domain(self):
        assert not self.crawler._is_valid_link("https://example.com/help/page.htm")

    def test_rejects_non_help_path(self):
        assert not self.crawler._is_valid_link(
            "https://www.site3d.co.uk/blog/post.htm"
        )

    def test_rejects_non_htm_extension(self):
        assert not self.crawler._is_valid_link(
            "https://www.site3d.co.uk/help/diagram.png"
        )

    def test_rejects_extensionless_url(self):
        assert not self.crawler._is_valid_link("https://www.site3d.co.uk/help/page")


class TestCrawl:
    @responses.activate
    def test_follows_internal_links(self):
        base = "https://www.site3d.co.uk/help/index.htm"
        responses.add(
            responses.GET,
            base,
            body='<html><body><a href="page2.htm">Next</a></body></html>',
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.site3d.co.uk/help/page2.htm",
            body="<html><body>leaf</body></html>",
            status=200,
        )

        crawler = Site3DCrawler(base)
        # Disable the 1s rate-limit for tests
        import scraper.crawler as mod

        original_sleep = mod.time.sleep
        mod.time.sleep = lambda _: None
        try:
            pages = crawler.crawl(max_pages=10)
        finally:
            mod.time.sleep = original_sleep

        assert base in pages
        assert "https://www.site3d.co.uk/help/page2.htm" in pages
        assert len(pages) == 2

    @responses.activate
    def test_respects_max_pages(self):
        base = "https://www.site3d.co.uk/help/index.htm"
        responses.add(
            responses.GET,
            base,
            body=(
                '<html><body>'
                '<a href="a.htm">a</a><a href="b.htm">b</a><a href="c.htm">c</a>'
                "</body></html>"
            ),
            status=200,
        )
        for leaf in ("a.htm", "b.htm", "c.htm"):
            responses.add(
                responses.GET,
                f"https://www.site3d.co.uk/help/{leaf}",
                body="<html><body>leaf</body></html>",
                status=200,
            )

        crawler = Site3DCrawler(base)
        import scraper.crawler as mod

        mod.time.sleep = lambda _: None
        pages = crawler.crawl(max_pages=2)
        assert len(pages) == 2

    @responses.activate
    def test_does_not_follow_external_links(self):
        base = "https://www.site3d.co.uk/help/index.htm"
        responses.add(
            responses.GET,
            base,
            body=(
                '<html><body>'
                '<a href="https://other.example.com/help/p.htm">outside</a>'
                '<a href="inner.htm">inside</a>'
                "</body></html>"
            ),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.site3d.co.uk/help/inner.htm",
            body="<html><body></body></html>",
            status=200,
        )

        crawler = Site3DCrawler(base)
        import scraper.crawler as mod

        mod.time.sleep = lambda _: None
        pages = crawler.crawl(max_pages=10)
        assert set(pages.keys()) == {base, "https://www.site3d.co.uk/help/inner.htm"}

    @responses.activate
    def test_handles_http_error_gracefully(self):
        base = "https://www.site3d.co.uk/help/index.htm"
        responses.add(
            responses.GET,
            base,
            body=(
                '<html><body>'
                '<a href="broken.htm">broken</a><a href="ok.htm">ok</a>'
                "</body></html>"
            ),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.site3d.co.uk/help/broken.htm",
            status=500,
        )
        responses.add(
            responses.GET,
            "https://www.site3d.co.uk/help/ok.htm",
            body="<html><body></body></html>",
            status=200,
        )

        crawler = Site3DCrawler(base)
        import scraper.crawler as mod

        mod.time.sleep = lambda _: None
        pages = crawler.crawl(max_pages=10)
        # Broken page should not appear, but crawl should complete
        assert "https://www.site3d.co.uk/help/broken.htm" not in pages
        assert "https://www.site3d.co.uk/help/ok.htm" in pages

    @responses.activate
    def test_deduplicates_via_fragment_stripping(self):
        base = "https://www.site3d.co.uk/help/index.htm"
        responses.add(
            responses.GET,
            base,
            body=(
                '<html><body>'
                '<a href="page.htm#section1">s1</a>'
                '<a href="page.htm#section2">s2</a>'
                "</body></html>"
            ),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://www.site3d.co.uk/help/page.htm",
            body="<html><body></body></html>",
            status=200,
        )

        crawler = Site3DCrawler(base)
        import scraper.crawler as mod

        mod.time.sleep = lambda _: None
        pages = crawler.crawl(max_pages=10)
        # Both fragment variants should collapse to one fetch
        assert list(pages.keys()).count(
            "https://www.site3d.co.uk/help/page.htm"
        ) == 1
