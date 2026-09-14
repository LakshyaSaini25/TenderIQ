from bs4 import BeautifulSoup
from typing import Dict, Any

class Parser:
    @staticmethod
    def parse_html(html_content: str) -> Dict[str, Any]:
        """
        Parses HTML content to extract title, clean text, and canonical URL.
        Strips scripts, styles, navigation, footers, forms, and select menus.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            
        # Extract canonical URL if present
        canonical_url = None
        canonical_tag = soup.find("link", rel="canonical")
        if canonical_tag and canonical_tag.get("href"):
            canonical_url = canonical_tag.get("href")
            
        # Remove non-content and form controls to prevent dropdown options pollution
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "svg", "button", "select", "option", "form"]):
            tag.decompose()
            
        # Extract text and let the normalizer handle whitespace formatting
        raw_text = soup.get_text(separator=' ', strip=True)
        
        return {
            "title": title,
            "canonical_url": canonical_url,
            "raw_text": raw_text
        }
