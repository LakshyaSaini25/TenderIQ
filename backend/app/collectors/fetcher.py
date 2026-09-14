import httpx
import logging
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

class Fetcher:
    @staticmethod
    async def fetch_html(
        url: str,
        timeout: int = 35,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Optional[str], Optional[str]]:
        """
        Fetches HTML from a public URL.
        Returns (status_code, html_content, error_message)
        """
        headers = dict(DEFAULT_HEADERS)
        if extra_headers:
            headers.update(extra_headers)

        try:
            async with httpx.AsyncClient(timeout=timeout, verify=False, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.status_code, response.text, None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return e.response.status_code, None, f"HTTP error: {e.response.status_code}"
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {url}: {e}")
            return 0, None, f"Request error (timeout or connection failed): {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return 0, None, f"Unexpected error: {str(e)}"
