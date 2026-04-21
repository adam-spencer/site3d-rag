from bs4 import BeautifulSoup

from scraper.preprocessor import (
    clean_filename_for_icon,
    is_icon,
    process_html,
    process_image_element,
)


def _img(**attrs):
    """Build a bs4 Tag for an <img> with the given attributes."""
    html_attrs = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    soup = BeautifulSoup(f"<img {html_attrs} />", "html.parser")
    return soup.find("img")


class TestIsIcon:
    def test_detects_icon_by_filename_keyword(self):
        assert is_icon(_img(src="/img/toolbar_new.png"), "toolbar_new.png")
        assert is_icon(_img(src="btn_save.png"), "btn_save.png")
        assert is_icon(_img(src="small_arrow.png"), "small_arrow.png")

    def test_detects_icon_by_small_dimensions(self):
        assert is_icon(_img(width="32", height="32"), "anything.png")
        assert is_icon(_img(width="48", height="48"), "anything.png")

    def test_large_dimensions_not_icon(self):
        assert not is_icon(_img(width="400", height="300"), "screen.png")

    def test_invalid_dimensions_fall_through_safely(self):
        # Non-integer dimensions shouldn't raise
        assert not is_icon(_img(width="auto", height="auto"), "screen.png")

    def test_missing_dimensions_not_icon(self):
        assert not is_icon(_img(src="/img/pic.png"), "pic.png")


class TestCleanFilenameForIcon:
    def test_removes_extension(self):
        assert clean_filename_for_icon("save_button.png") == "save button"

    def test_replaces_dashes_and_underscores(self):
        assert clean_filename_for_icon("new-doc_icon.gif") == "new doc icon"


class TestProcessImageElement:
    def test_icon_output_shape(self):
        tag = _img(src="icons/toolbar_new.png", alt="New")
        out = process_image_element(tag)
        assert out == "[Icon: New](icons/toolbar_new.png)"

    def test_icon_fallback_to_cleaned_filename_when_no_alt(self):
        tag = _img(src="icons/toolbar_new.png")
        out = process_image_element(tag)
        assert out == "[Icon: toolbar new](icons/toolbar_new.png)"

    def test_screenshot_output_shape(self):
        tag = _img(src="screens/alignment.png", alt="Alignment dialog")
        out = process_image_element(tag)
        assert out == "[Screenshot: alignment.png - Alignment dialog](screens/alignment.png)"

    def test_screenshot_without_alt(self):
        tag = _img(src="screens/alignment.png")
        out = process_image_element(tag)
        assert out == "[Screenshot: alignment.png](screens/alignment.png)"


class TestProcessHtml:
    def test_replaces_images_with_placeholders(self):
        html = (
            "<html><head><title>Doc</title></head>"
            '<body><p>Before</p><img src="icons/btn.png" alt="Save"/>'
            "<p>After</p></body></html>"
        )
        out, title = process_html(html)
        assert title == "Doc"
        assert "<img" not in out
        assert "[Icon: Save]" in out

    def test_extracts_title(self):
        _, title = process_html(
            "<html><head><title>My Page</title></head><body></body></html>"
        )
        assert title == "My Page"

    def test_missing_title_returns_placeholder(self):
        _, title = process_html("<html><body><p>no title</p></body></html>")
        assert title == "Unknown Title"
