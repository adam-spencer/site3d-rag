import markdownify
import re


def convert_to_markdown(html_content: str) -> str:
    """Convert HTML string to Markdown, preserving links and using ATX headers."""
    # heading_style="ATX" ensures markdown uses '#' instead of underlines
    # We strip out noise tags for a cleaner conversion
    md_text = markdownify.markdownify(
        html_content,
        heading_style="ATX",
        strip=["script", "style", "nav", "footer", "iframe"],
    )

    # Collapse 3+ consecutive newlines into 2 to keep layout neat
    md_text = re.sub(r"\n{3,}", "\n\n", md_text)

    return md_text.strip()
