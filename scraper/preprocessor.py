import os
import re
from bs4 import BeautifulSoup
from typing import Tuple

def is_icon(img, filename: str) -> bool:
    """Determine if a given img tag is an icon based on heuristics."""
    keywords = ['icon', 'button', 'btn', 'toolbar', 'small']
    if any(keyword in filename.lower() for keyword in keywords):
        return True
    
    width = img.get('width')
    height = img.get('height')
    
    try:
        # Check if width and height are small explicitly
        if width and int(width) <= 48 and height and int(height) <= 48:
            return True
    except (ValueError, TypeError):
        pass
        
    return False

def clean_filename_for_icon(filename: str) -> str:
    """Format icon filename to string format."""
    name_without_ext = os.path.splitext(filename)[0]
    return name_without_ext.replace('_', ' ').replace('-', ' ').strip()

def process_image_element(img) -> str:
    """Process a single image tag and return the replacement text.
    Designed modularly to allow Vision API swapping in the future.
    """
    src = img.get('src', '')
    filename = os.path.basename(src) if src else 'unknown'
    alt_text = img.get('alt', '').strip()

    if is_icon(img, filename):
        if alt_text:
            return f"[Icon: {alt_text}]({src})"
        else:
            return f"[Icon: {clean_filename_for_icon(filename)}]({src})"
    else:
        # It's a screenshot
        screenshot_text = f"[Screenshot: {filename}"
        if alt_text:
            screenshot_text += f" - {alt_text}"
        screenshot_text += f"]({src})"
        return screenshot_text

def process_html(raw_html: str) -> Tuple[str, str]:
    """Process raw HTML, replacing images and returning clean HTML and page title."""
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Extract title
    title_tag = soup.find('title')
    page_title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"
    
    # Process images
    for img in soup.find_all('img'):
        replacement_text = process_image_element(img)
        img.replace_with(replacement_text)
        
    return str(soup), page_title
