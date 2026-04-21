import logging
import time
import requests
from urllib.parse import urljoin, urldefrag, urlparse
from bs4 import BeautifulSoup
from typing import Dict

logger = logging.getLogger(__name__)


class Site3DCrawler:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.visited = set()
        self.queue = [base_url]
        self.pages: Dict[str, str] = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _is_valid_link(self, url: str) -> bool:
        """Only allow site3d help pages."""
        parsed_url = urlparse(url)
        if "site3d.co.uk" not in parsed_url.netloc:
            return False
        if "/help/" not in parsed_url.path:
            return False
        if not (parsed_url.path.endswith(".htm") or parsed_url.path.endswith(".html")):
            return False
        return True

    def crawl(self, max_pages: int = 100) -> Dict[str, str]:
        logger.info("Starting crawler from %s", self.base_url)

        while self.queue and len(self.visited) < max_pages:
            current_url = self.queue.pop(0)
            clean_url, _ = urldefrag(current_url)

            if clean_url in self.visited:
                continue

            self.visited.add(clean_url)
            logger.info("[%d/%d] Fetching: %s", len(self.visited), max_pages, clean_url)

            try:
                response = requests.get(clean_url, headers=self.headers, timeout=10)
                response.raise_for_status()

                html_content = response.text
                self.pages[clean_url] = html_content

                soup = BeautifulSoup(html_content, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    raw_href = a_tag["href"]
                    full_url = urljoin(clean_url, raw_href)
                    defrag_url, _ = urldefrag(full_url)

                    if (
                        self._is_valid_link(defrag_url)
                        and defrag_url not in self.visited
                        and defrag_url not in self.queue
                    ):
                        self.queue.append(defrag_url)

            except requests.RequestException as e:
                logger.warning("Failed to fetch %s: %s", clean_url, e)

            # Rate-limit
            time.sleep(1.0)

        logger.info("Crawl completed. Successfully fetched %d pages.", len(self.pages))
        return self.pages
