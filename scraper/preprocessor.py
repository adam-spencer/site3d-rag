import os
from bs4 import BeautifulSoup, Tag
from typing import Tuple


def _attr(img: Tag, name: str, default: str = "") -> str:
    """Return a single-string attribute value. bs4 returns list[str] for
    multi-valued attributes like ``class``; we never use those here."""
    value = img.get(name, default)
    if isinstance(value, list):
        return " ".join(value)
    return value


def is_icon(img: Tag, filename: str) -> bool:
    """Heuristic check for icon-sized images."""
    keywords = ["icon", "button", "btn", "toolbar", "small"]
    if any(keyword in filename.lower() for keyword in keywords):
        return True

    width = _attr(img, "width")
    height = _attr(img, "height")

    try:
        if width and int(width) <= 48 and height and int(height) <= 48:
            return True
    except (ValueError, TypeError):
        pass

    return False


def clean_filename_for_icon(filename: str) -> str:
    """Convert filename to readable label."""
    name_without_ext = os.path.splitext(filename)[0]
    return name_without_ext.replace("_", " ").replace("-", " ").strip()


def process_image_element(img: Tag) -> str:
    """Convert an img tag to a markdown placeholder."""
    src = _attr(img, "src")
    filename = os.path.basename(src) if src else "unknown"
    alt_text = _attr(img, "alt").strip()

    if is_icon(img, filename):
        if alt_text:
            return f"[Icon: {alt_text}]({src})"
        else:
            return f"[Icon: {clean_filename_for_icon(filename)}]({src})"
    else:
        screenshot_text = f"[Screenshot: {filename}"
        if alt_text:
            screenshot_text += f" - {alt_text}"
        screenshot_text += f"]({src})"
        return screenshot_text


def process_html(raw_html: str) -> Tuple[str, str]:
    """Replace images with markdown placeholders and extract page title."""
    soup = BeautifulSoup(raw_html, "html.parser")

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"

    for img in soup.find_all("img"):
        replacement_text = process_image_element(img)
        img.replace_with(replacement_text)

    return str(soup), page_title
