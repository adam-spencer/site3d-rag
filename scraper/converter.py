import markdownify
import re


def convert_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown."""
    md_text = markdownify.markdownify(
        html_content,
        heading_style="ATX",
        strip=["script", "style", "nav", "footer", "iframe"],
    )

    md_text = re.sub(r"\n{3,}", "\n\n", md_text)

    return md_text.strip()
