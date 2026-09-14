import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from app.collectors.adapters.base import BaseSourceAdapter
from app.collectors.fetcher import Fetcher
from app.collectors.parser import Parser
from app.collectors.normalizer import Normalizer

logger = logging.getLogger(__name__)

class PublicTenderAdapter(BaseSourceAdapter):
    """
    Adapter for Public Government Tender Portals.
    Supports HTML portal listings as well as RSS/XML feeds (e.g. CPPP, GeM, Tender.gov.in, E-Procurement).
    """

    @classmethod
    def supports(cls, source: Dict[str, Any]) -> bool:
        source_type = source.get("type", "")
        url = source.get("url", "").lower()
        name = source.get("name", "").lower()

        if source_type in ["TENDER_PORTAL", "GOVERNMENT", "PROJECT_PORTAL"]:
            return True
        if "tender" in url or "procure" in url or "gov" in url or "tender" in name:
            return True
        return False

    async def discover_listing_urls(self, source_url: str) -> List[str]:
        """
        Discovers tender links from the source URL (RSS feed items or HTML listing pages).
        """
        status_code, content, error = await Fetcher.fetch_html(source_url)
        if error or not content:
            logger.error(f"Failed to fetch discovery page {source_url}: {error}")
            return [source_url]  # Fallback to source URL itself

        # Check if content is XML / RSS Feed
        if "<rss" in content.lower() or "<feed" in content.lower() or "xml" in content[:100].lower():
            urls = self._parse_rss_items(content, source_url)
            if urls:
                return urls

        # Otherwise parse HTML for tender detail links
        soup = BeautifulSoup(content, "html.parser")
        tender_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            href_lower = href.lower()
            text_lower = a.get_text().lower()

            # Target links that look like tender detail pages
            if any(k in href_lower or k in text_lower for k in [
                "tender", "notice", "bid", "rfp", "detail", "view", "display", "eprocure", "cppp"
            ]):
                if href.startswith("http://") or href.startswith("https://"):
                    full_url = href
                elif href.startswith("/"):
                    # Join with domain base
                    parts = source_url.split("/")
                    base_domain = f"{parts[0]}//{parts[2]}"
                    full_url = f"{base_domain}{href}"
                else:
                    full_url = f"{source_url.rstrip('/')}/{href}"

                tender_urls.add(full_url)

        # If no links discovered, treat the page itself as a tender listing item
        if not tender_urls:
            tender_urls.add(source_url)

        return list(tender_urls)[:50]  # Cap at 50 per run for respectful rate limiting

    def _parse_rss_items(self, xml_content: str, base_url: str) -> List[str]:
        urls = []
        soup = BeautifulSoup(xml_content, "xml")
        items = soup.find_all("item") or soup.find_all("entry")
        for item in items:
            link = item.find("link")
            if link:
                url_text = link.get_text().strip() or link.get("href", "").strip()
                if url_text:
                    urls.append(url_text)
        return urls

    async def extract_opportunity(
        self, url: str, html_or_content: str, source_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts structured tender fields from the fetched page content or XML item.
        """
        if not html_or_content:
            return None

        try:
            # Check if this is an XML item string or full HTML
            if "<item>" in html_or_content or "<entry>" in html_or_content:
                return self._extract_from_rss_item(url, html_or_content, source_id)
            else:
                return self._extract_from_html(url, html_or_content, source_id)
        except Exception as e:
            logger.error(f"Error extracting opportunity from {url}: {e}")
            return None

    def _extract_from_html(self, url: str, html: str, source_id: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        parsed = Parser.parse_html(html)
        raw_text = parsed.get("raw_text", "")

        title = parsed.get("title", "").strip()
        if not title or title.lower() in ["home", "index", "tenders"]:
            # Try h1 or meta title
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text().strip()
            else:
                title = f"Tender Opportunity - {url.split('/')[-1]}"

        # Regex extractors
        ref_num = self._extract_regex([
            r"(?:Tender\s*(?:Ref|ID|No|Num|Number|Code)[\s:=#]+)([A-Za-z0-9/\-_]{4,30})",
            r"(?:Ref\s*(?:No|Num|Number)[\s:=#]+)([A-Za-z0-9/\-_]{4,30})",
            r"(?:NIT\s*(?:No|Num|Number)[\s:=#]+)([A-Za-z0-9/\-_]{4,30})",
            r"(?:BID\s*(?:No|ID)[\s:=#]+)([A-Za-z0-9/\-_]{4,30})"
        ], raw_text)

        org = self._extract_regex([
            r"(?:Organisation|Organization|Department|Issuer|Authority)[\s:=]+([A-Za-z0-9\s,\.\-]{3,60})",
            r"(?:Issued By)[\s:=]+([A-Za-z0-9\s,\.\-]{3,60})"
        ], raw_text)

        location = self._extract_regex([
            r"(?:Location|State|City|Place)[\s:=]+([A-Za-z0-9\s,\-]{3,40})",
            r"(?:Work Location)[\s:=]+([A-Za-z0-9\s,\-]{3,40})"
        ], raw_text)

        val = self._extract_regex([
            r"(?:Tender\s*Value|Estimated\s*Cost|Amount|EMD|Value)[\s:=]+(₹?\s*[\d,]+(?:\.\d+)?(?:\s*(?:Lakh|Crore|L|Cr))?)",
            r"(₹\s*[\d,]+(?:\.\d+)?)"
        ], raw_text)

        closing_date = self._parse_date_from_text([
            r"(?:Closing\s*Date|Deadline|Due\s*Date|Last\s*Date|Submission\s*End)[\s:=]+([A-Za-z0-9\s,\-:\.\/]{6,25})",
            r"(?:End\s*Date)[\s:=]+([A-Za-z0-9\s,\-:\.\/]{6,25})"
        ], raw_text)

        pub_date = self._parse_date_from_text([
            r"(?:Published\s*Date|Publish\s*Date|Start\s*Date|Date\s*of\s*Issue)[\s:=]+([A-Za-z0-9\s,\-:\.\/]{6,25})"
        ], raw_text)

        # Validate that this is a genuine tender notice, not a generic navigation page
        if not ref_num and not closing_date:
            logger.info(f"Skipping {url}: No valid tender reference or deadline found.")
            return None

        # Status determination
        status = "OPEN"
        if closing_date and closing_date < datetime.now(timezone.utc):
            status = "CLOSED"

        return {
            "source_id": source_id,
            "type": "TENDER",
            "title": title[:300],
            "reference_number": ref_num,
            "description": Normalizer.normalize_text(raw_text[:1000]),
            "organization": org,
            "department": None,
            "location": location,
            "category": None,
            "value": val,
            "published_at": pub_date,
            "deadline": closing_date,
            "source_url": url,
            "status": status
        }

    def _extract_from_rss_item(self, url: str, xml_item: str, source_id: str) -> Dict[str, Any]:
        soup = BeautifulSoup(xml_item, "xml")
        title_tag = soup.find("title")
        desc_tag = soup.find("description") or soup.find("content")
        pub_tag = soup.find("pubDate") or soup.find("published")

        title = title_tag.get_text().strip() if title_tag else "Tender Notice"
        desc = Normalizer.normalize_text(desc_tag.get_text()) if desc_tag else ""
        pub_date = None
        if pub_tag:
            try:
                pub_date = date_parser.parse(pub_tag.get_text().strip()).replace(tzinfo=timezone.utc)
            except Exception:
                pass

        ref_num = self._extract_regex([
            r"(?:Ref|ID|No|NIT)[\s:=#]+([A-Za-z0-9/\-_]{4,30})"
        ], f"{title} {desc}")

        return {
            "source_id": source_id,
            "type": "TENDER",
            "title": title[:300],
            "reference_number": ref_num,
            "description": desc[:1000],
            "organization": None,
            "department": None,
            "location": None,
            "category": None,
            "value": None,
            "published_at": pub_date,
            "deadline": None,
            "source_url": url,
            "status": "OPEN"
        }

    def _extract_regex(self, patterns: List[str], text: str) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                res = match.group(1).strip()
                if len(res) > 1:
                    return res
        return None

    def _parse_date_from_text(self, patterns: List[str], text: str) -> Optional[datetime]:
        date_str = self._extract_regex(patterns, text)
        if date_str:
            try:
                dt = date_parser.parse(date_str, fuzzy=True)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None
        return None

