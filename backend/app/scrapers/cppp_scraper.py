import asyncio
import base64
import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

try:
    import ddddocr
except ImportError:
    ddddocr = None

from .base import BaseTenderScraper
from .schema import TenderSchema, TenderDocument
from app.repositories.scraped_tender_repository import ScrapedTenderRepository

logger = logging.getLogger("scraper.cppp")


class CPPPConfig:
    BASE_URL = "https://eprocure.gov.in"
    LISTING_URL = "https://eprocure.gov.in/cppp/latestactivetendersnew"
    CPPP_DATA_URL = "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"
    TIMEOUT = 30.0
    MAX_CAPTCHA_RETRIES = 3
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


class CPPPScraper(BaseTenderScraper):
    """
    Scraper specifically designed for Central Public Procurement Portal (CPPP / eprocure.gov.in).
    Extracts structured tender records from the active tenders table,
    solves CAPTCHAs automatically to unlock deep tender details, specifications,
    and supporting document download links.
    """

    def __init__(self, repository: Optional[ScrapedTenderRepository] = None):
        super().__init__(source_name="CPPP", repository=repository)
        self.config = CPPPConfig
        self._ocr = None
        self._client: Optional[httpx.AsyncClient] = None
        self._session_primed = False

    def _get_ocr(self):
        if self._ocr is None and ddddocr is not None:
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=False,
                headers=self.config.DEFAULT_HEADERS,
                timeout=self.config.TIMEOUT,
                follow_redirects=True
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            self._session_primed = False

    async def fetch(self, page: int = 1, **kwargs) -> Optional[str]:
        """
        Fetches the HTML listing page for the given page number.
        CPPP uses a Base64-encoded URL parameter for page > 1.
        """
        client = await self._get_client()

        # Prime session cookies once
        if not self._session_primed:
            try:
                await client.get(self.config.BASE_URL + "/cppp/")
                self._session_primed = True
            except Exception:
                pass

        if page == 1:
            target_url = self.config.CPPP_DATA_URL
        else:
            raw_url = f"{self.config.CPPP_DATA_URL}?page={page}"
            b64_url = base64.b64encode(raw_url.encode()).decode()
            target_url = f"{self.config.CPPP_DATA_URL}?url={b64_url}"

        headers = {"Referer": self.config.BASE_URL + "/cppp/"}

        for attempt in range(3):
            try:
                resp = await client.get(target_url, headers=headers)
                if resp.status_code == 200:
                    if "unexpected error" in resp.text.lower() and len(resp.text) < 200:
                        self.logger.warning(f"[CPPP] Transient Drupal 500 on page {page}, retrying ({attempt + 1}/3)...")
                        await asyncio.sleep(1.5)
                        continue
                    return resp.text
                else:
                    self.logger.warning(f"[CPPP] HTTP {resp.status_code} fetching page {page}")
            except Exception as e:
                self.logger.warning(f"[CPPP] Request error page {page}: {e}, retrying ({attempt + 1}/3)...")
                await asyncio.sleep(1.5)

        return None

    def parse(self, raw_content: str) -> BeautifulSoup:
        return BeautifulSoup(raw_content, "html.parser")

    def extract_tenders(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Extracts raw tender row dictionaries from the listing table.
        """
        table = soup.find("table", id="table") or soup.find("table", class_="list_table")
        if not table:
            # Fallback scan for table with Sl.No
            for t in soup.find_all("table"):
                if "Sl.No" in t.get_text():
                    table = t
                    break

        if not table:
            return []

        rows: List[Dict[str, Any]] = []

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue  # Header or summary row

            sl_no = tds[0].get_text(strip=True)
            pub_date_str = tds[1].get_text(strip=True)
            close_date_str = tds[2].get_text(strip=True)
            open_date_str = tds[3].get_text(strip=True)

            # Col 4: Title / Ref.No. / Tender Id
            col4 = tds[4]
            a_tag = col4.find("a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            detail_href = a_tag.get("href", "").strip()
            detail_url = urljoin(self.config.BASE_URL, detail_href) if detail_href else ""

            # Extract trailing ref num and tender ID from text
            full_col4_text = col4.get_text(strip=True)
            trailing = full_col4_text[len(title):].strip()
            if trailing.startswith("/"):
                trailing = trailing[1:]

            parts = trailing.rsplit("/", 1)
            if len(parts) == 2:
                ref_num, tender_id = parts[0].strip(), parts[1].strip()
            else:
                ref_num, tender_id = trailing.strip() or None, None

            # Col 5: Organisation Name
            org_name = tds[5].get_text(strip=True)

            # Unique source ID (prefer tender_id -> ref_num -> generated hash)
            source_id = tender_id or ref_num or f"CPPP_{sl_no}_{abs(hash(title))}"

            rows.append({
                "sl_no": sl_no,
                "source_id": source_id,
                "title": title,
                "reference_no": ref_num or tender_id,
                "tender_id": tender_id,
                "organisation": org_name,
                "pub_date_str": pub_date_str,
                "close_date_str": close_date_str,
                "open_date_str": open_date_str,
                "detail_url": detail_url,
                "detail_solved": False,
                "description": None,
                "documents": [],
                "tender_fee": None,
                "emd_amount": None,
                "tender_value": None,
                "category": None,
                "tender_type": None,
                "location": None,
                "pincode": None,
                "inviting_authority_name": None,
                "inviting_authority_address": None,
            })

        return rows

    async def enrich_details(self, raw_tenders: List[Dict[str, Any]]):
        """
        Visits each tender's detail page, solves the image CAPTCHA in memory,
        and enriches with full specs, location, and document links.
        """
        ocr = self._get_ocr()
        if not ocr:
            self.logger.warning("[CPPP] ddddocr not installed or initialized; skipping detail enrichment.")
            return

        headers = dict(self.config.DEFAULT_HEADERS)
        headers["Referer"] = self.config.CPPP_DATA_URL

        async with httpx.AsyncClient(
            verify=False,
            headers=headers,
            timeout=self.config.TIMEOUT,
            follow_redirects=True
        ) as client:
            # Prime session
            try:
                await client.get(self.config.LISTING_URL)
            except Exception:
                pass

            for item in raw_tenders:
                detail_url = item.get("detail_url")
                if not detail_url or "/tendersfullview/" not in detail_url:
                    continue

                try:
                    detail_html = await self._solve_and_fetch_detail(client, detail_url, ocr)
                    if detail_html:
                        self._parse_detail_html(detail_html, item)
                        item["detail_solved"] = True
                    await asyncio.sleep(0.4)  # Politeness interval
                except Exception as e:
                    self.logger.warning(f"[CPPP] Failed to enrich detail for {item.get('source_id')}: {e}")

    async def _solve_and_fetch_detail(self, client: httpx.AsyncClient, detail_url: str, ocr: Any) -> Optional[str]:
        """
        Navigates into detail page, solves the CAPTCHA, and returns the unlocked HTML.
        """
        try:
            r = await client.get(detail_url, headers={"Referer": self.config.CPPP_DATA_URL})
            if r.status_code != 200:
                return None
            curr_html = r.text
        except Exception:
            return None

        # Check if already unlocked (no captcha form)
        soup = BeautifulSoup(curr_html, "html.parser")
        form = soup.find("form", id=lambda x: x and "tender" in x.lower())
        if not form or "tenderfullview-tenders" not in (form.get("id") or ""):
            return curr_html

        # Loop through solve attempts
        for attempt in range(self.config.MAX_CAPTCHA_RETRIES):
            soup = BeautifulSoup(curr_html, "html.parser")
            form = soup.find("form", id=lambda x: x and "tender" in x.lower())
            if not form or "tenderfullview-tenders" not in (form.get("id") or ""):
                return curr_html

            img = soup.find("img", src=lambda s: s and "captcha" in s.lower())
            if not img:
                return curr_html

            img_src = img.get("src", "")
            img_url = urljoin(self.config.BASE_URL, img_src)

            try:
                img_resp = await client.get(img_url, headers={"Referer": detail_url})
                if img_resp.status_code != 200 or not img_resp.content:
                    await asyncio.sleep(0.5)
                    continue

                code = ocr.classification(img_resp.content).strip().replace(" ", "")

                # Collect form inputs
                form_data = {
                    inp.get("name"): inp.get("value", "")
                    for inp in form.find_all("input")
                    if inp.get("name")
                }
                form_data["captcha_response"] = code
                form_data["op"] = "Submit"

                action = form.get("action") or detail_url
                post_url = urljoin(self.config.BASE_URL, action)

                post_resp = await client.post(post_url, data=form_data, headers={"Referer": detail_url})
                if post_resp.status_code == 200:
                    curr_html = post_resp.text
                    if "tenderfullview-tenders" not in curr_html and (
                        "Work Description" in curr_html or "Organisation Chain" in curr_html or "Tender Fee" in curr_html
                    ):
                        return curr_html
                await asyncio.sleep(0.5)
            except Exception as ex:
                self.logger.debug(f"[CPPP] Solve attempt {attempt + 1} exception: {ex}")
                await asyncio.sleep(0.5)

        return None

    def _parse_detail_html(self, html: str, item: Dict[str, Any]):
        """
        Parses key-value rows and document links from unlocked detail HTML.
        """
        soup = BeautifulSoup(html, "html.parser")
        raw_fields: Dict[str, str] = {}
        docs: List[Dict[str, str]] = []

        for tr in soup.find_all("tr"):
            # Check document links
            for a in tr.find_all("a", href=True):
                href = a["href"].strip()
                title = a.get_text(strip=True) or a.get("title", "").strip() or "Tender Document"
                if href and ("tendersfullview" not in href) and ("javascript:" not in href) and not href.startswith("#"):
                    full_href = urljoin(self.config.BASE_URL, href)
                    if not any(ign in title.lower() for ign in ["skip to", "screen reader", "about us", "home", "faq"]):
                        if not any(d["url"] == full_href for d in docs):
                            docs.append({"name": title, "url": full_href, "type": "tender_document"})

            # Parse key-value cells
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            i = 0
            while i < len(cells):
                k = cells[i].rstrip(":").strip()
                if not k:
                    i += 1
                    continue
                if i + 1 < len(cells) and cells[i + 1] == ":":
                    val = cells[i + 2] if i + 2 < len(cells) else ""
                    i += 3
                elif i + 1 < len(cells):
                    val = cells[i + 1]
                    i += 2
                else:
                    break

                clean_k = k.replace("*", "").strip()
                if clean_k and val and len(clean_k) < 80:
                    raw_fields[clean_k] = val.strip()

        # Enrich item fields
        org_chain = raw_fields.get("Organisation Chain") or raw_fields.get("Organisation Name")
        if org_chain:
            item["department"] = org_chain

        work_desc = raw_fields.get("Work Description") or raw_fields.get("Tender Title")
        if work_desc:
            item["description"] = work_desc

        loc = raw_fields.get("Location")
        if loc and loc not in ["--", "NA", "N/A"]:
            item["location"] = loc

        pincode = raw_fields.get("Pincode")
        if pincode and pincode not in ["--", "NA", "N/A"]:
            item["pincode"] = pincode

        category = raw_fields.get("Tender Category") or raw_fields.get("Product Category")
        if category:
            item["category"] = category

        item["tender_type"] = raw_fields.get("Tender Type")

        # Parse tender fee & EMD
        fee_str = raw_fields.get("Tender Fee in ₹") or raw_fields.get("Tender Fee")
        if fee_str:
            item["tender_fee"] = self._parse_numeric_amount(fee_str)

        emd_str = raw_fields.get("EMD Amount in ₹") or raw_fields.get("EMD Amount") or raw_fields.get("EMD")
        if emd_str:
            item["emd_amount"] = self._parse_numeric_amount(emd_str)

        val_str = raw_fields.get("Tender Value in ₹") or raw_fields.get("Tender Value")
        if val_str:
            item["tender_value"] = self._parse_numeric_amount(val_str)

        item["inviting_authority_name"] = raw_fields.get("Name")
        item["inviting_authority_address"] = raw_fields.get("Address")
        item["documents"] = docs

    def normalize(self, raw_tender: Dict[str, Any]) -> TenderSchema:
        """
        Normalizes CPPP-specific extracted dictionary into TenderSchema.
        """
        pub_dt = self._parse_date(raw_tender.get("pub_date_str"))
        close_dt = self._parse_date(raw_tender.get("close_date_str"))
        open_dt = self._parse_date(raw_tender.get("open_date_str"))

        # Determine OPEN / CLOSED
        status = "OPEN"
        now = datetime.now(timezone.utc)
        if close_dt and close_dt < now:
            status = "CLOSED"

        # Heuristic location if not solved from detail
        location = raw_tender.get("location")
        if not location:
            location = self._extract_location(
                raw_tender.get("title", ""),
                raw_tender.get("organisation", "")
            )

        # Fallback description if detail was not unlocked
        description = raw_tender.get("description")
        if not description:
            description = (
                f"Tender {raw_tender.get('reference_no') or ''} issued by {raw_tender.get('organisation')}. "
                f"Closing Date: {raw_tender.get('close_date_str')}. "
                f"Opening Date: {raw_tender.get('open_date_str')}."
            )

        docs = [
            TenderDocument(name=d.get("name", "Document"), url=d.get("url", ""), type=d.get("type", "tender_document"))
            for d in raw_tender.get("documents", [])
            if d.get("url")
        ]

        return TenderSchema(
            source=self.source_name,
            source_id=str(raw_tender.get("source_id")),
            title=raw_tender.get("title", "").strip(),
            reference_no=raw_tender.get("reference_no"),
            organisation=raw_tender.get("organisation"),
            department=raw_tender.get("department"),
            category=raw_tender.get("category", "General"),
            tender_type=raw_tender.get("tender_type"),
            location=location,
            pincode=raw_tender.get("pincode"),
            tender_value=raw_tender.get("tender_value"),
            emd_amount=raw_tender.get("emd_amount"),
            tender_fee=raw_tender.get("tender_fee"),
            publication_date=pub_dt,
            closing_date=close_dt,
            opening_date=open_dt,
            status=status,
            description=description,
            source_url=raw_tender.get("detail_url") or self.config.LISTING_URL,
            documents=docs,
            inviting_authority_name=raw_tender.get("inviting_authority_name"),
            inviting_authority_address=raw_tender.get("inviting_authority_address"),
            detail_solved=bool(raw_tender.get("detail_solved", False)),
            raw_data={
                "sl_no": raw_tender.get("sl_no"),
                "pub_date_str": raw_tender.get("pub_date_str"),
                "close_date_str": raw_tender.get("close_date_str"),
                "open_date_str": raw_tender.get("open_date_str"),
            }
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str or date_str in ["--", "NA", "N/A"]:
            return None
        try:
            dt = date_parser.parse(date_str, fuzzy=True)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def _parse_numeric_amount(self, text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        clean = re.sub(r"[^\d.]", "", text.strip())
        try:
            val = float(clean)
            return val if val > 0 else None
        except Exception:
            return None

    def _extract_location(self, title: str, org: str) -> Optional[str]:
        text = f"{title} {org}".upper()
        cities = [
            "DELHI", "MUMBAI", "KOLKATA", "CHENNAI", "BANGALORE", "HYDERABAD",
            "AHMEDABAD", "PUNE", "LUCKNOW", "BHOPAL", "PATNA", "JAIPUR",
            "GUWAHATI", "DEHRADUN", "RANCHI", "RAIPUR", "CHANDIGARH", "SRINAGAR",
            "KOCHI", "THIRUVANANTHAPURAM", "BHUBANESWAR", "INDORE", "NAGPUR"
        ]
        for c in cities:
            if re.search(r"\b" + c + r"\b", text):
                return c.title()
        return None
