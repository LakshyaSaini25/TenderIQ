import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.collectors.adapters.base import BaseSourceAdapter
from app.collectors.fetcher import Fetcher
from app.collectors.normalizer import Normalizer

logger = logging.getLogger(__name__)


from app.collectors.captcha_solver import CaptchaSolver


class EprocureAdapter(BaseSourceAdapter):
    """
    Adapter specifically designed for Central Public Procurement Portal (CPPP / eprocure.gov.in).
    Extracts high-precision structured tender records from the active tenders table,
    solves CAPTCHAs automatically to unlock deep tender details, specifications,
    and supporting document download links.
    """

    @classmethod
    def supports(cls, source: Dict[str, Any]) -> bool:
        url = source.get("url", "").lower()
        name = source.get("name", "").lower()
        return "eprocure.gov.in" in url or "cppp" in url or "cppp" in name or "eprocure" in name

    async def discover_listing_urls(self, source_url: str) -> List[str]:
        """
        Returns the listing URL to fetch.
        """
        return [source_url]

    async def extract_opportunity(
        self,
        url: str,
        html: str,
        source_id: str,
        fetch_details: bool = True,
        client: Optional[Any] = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Extracts structured tender records from the CPPP listing table and
        enriches each tender with full details & documents via automated captcha solving.
        """
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        
        # Locate the main tenders table containing 'Sl.No' header
        table = None
        for t in soup.find_all("table"):
            text = t.get_text()
            if "Sl.No" in text and ("Title/Ref.No./Tender Id" in text or "Title" in text):
                table = t
                break

        if not table:
            logger.warning(f"No CPPP tenders table found on {url}")
            return None

        opportunities: List[Dict[str, Any]] = []

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue  # Skip headers or metadata rows

            # Col 0: Sl.No
            sl_no = tds[0].get_text(strip=True)

            # Col 1: e-Published Date
            pub_date_str = tds[1].get_text(strip=True)
            published_at = self._parse_date(pub_date_str)

            # Col 2: Bid Submission Closing Date (Deadline)
            close_date_str = tds[2].get_text(strip=True)
            deadline = self._parse_date(close_date_str)

            # Col 3: Tender Opening Date
            open_date_str = tds[3].get_text(strip=True)
            opening_at = self._parse_date(open_date_str)

            # Col 4: Title / Ref.No. / Tender Id
            col4 = tds[4]
            a_tag = col4.find("a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            detail_href = a_tag.get("href", "").strip()
            if detail_href.startswith("/"):
                detail_url = f"https://eprocure.gov.in{detail_href}"
            else:
                detail_url = detail_href or url

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

            # Location extraction heuristic from title or org
            location = self._extract_location(title, org_name)

            # Status determination
            status = "OPEN"
            if deadline and deadline < datetime.now(timezone.utc):
                status = "CLOSED"

            desc = (
                f"Tender {tender_id or ref_num or ''} for {title}. "
                f"Issuing Organisation: {org_name}. "
                f"Published on {pub_date_str}. "
                f"Bid Submission Closing: {close_date_str}. "
                f"Opening Date: {open_date_str}."
            )

            raw_text = (
                f"Tender Title: {title}\n"
                f"Reference Number: {ref_num}\n"
                f"Tender ID: {tender_id}\n"
                f"Organization: {org_name}\n"
                f"Published Date: {pub_date_str}\n"
                f"Closing Date: {close_date_str}\n"
                f"Opening Date: {open_date_str}\n"
                f"Source URL: {detail_url}"
            )

            opp_dict = {
                "source_id": source_id,
                "type": "TENDER",
                "title": title[:300],
                "reference_number": ref_num or tender_id,
                "reference_number_raw": trailing or None,
                "description": desc[:1500],
                "organization": org_name,
                "department": None,
                "location": location,
                "category_id": None,
                "category_name": "General",
                "value": None,
                "currency": "INR",
                "value_text": None,
                "published_at": published_at,
                "deadline": deadline,
                "source_url": detail_url,
                "status": status,
                "is_opportunity": True,
                "detection_reason": f"Structured CPPP Tender Row #{sl_no}",
                "raw_content": raw_text,
                "raw_html": str(tr),
                "tender_fee": None,
                "emd_amount": None,
                "tender_category": None,
                "product_category": None,
                "pincode": None,
                "inviting_authority_name": None,
                "inviting_authority_address": None,
                "documents": [],
                "detail_solved": False,
            }

            opportunities.append(opp_dict)

        # If fetch_details is enabled and we have detail URLs, enrich with captcha solver
        if fetch_details and opportunities:
            await self._enrich_tenders_with_details(opportunities, list_url=url, client=client)

        logger.info(f"EprocureAdapter successfully extracted {len(opportunities)} tenders from {url}")
        return opportunities if opportunities else None

    async def _enrich_tenders_with_details(
        self,
        opportunities: List[Dict[str, Any]],
        list_url: str,
        client: Optional[Any] = None
    ) -> None:
        """
        Navigates into each tender's detail page, solves the captcha, and merges rich fields.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async def enrich_single(session: Any, opp: Dict[str, Any]):
            detail_url = opp.get("source_url")
            if not detail_url or "/cppp/tendersfullview/" not in detail_url:
                return

            try:
                detail_html, err = await CaptchaSolver.solve_and_fetch_detail(session, detail_url, list_url)
                if not detail_html:
                    logger.warning(f"Could not solve detail for {opp.get('reference_number')}: {err}")
                    return

                fields, docs = CaptchaSolver.parse_cppp_detail_html(detail_html)
                if not fields and not docs:
                    return

                # Enrich fields
                opp["detail_solved"] = True
                if fields.get("work_description"):
                    opp["description"] = fields["work_description"][:2000]
                if fields.get("organization"):
                    opp["organization"] = fields["organization"]
                if fields.get("location"):
                    opp["location"] = fields["location"]
                if fields.get("pincode"):
                    opp["pincode"] = fields["pincode"]
                if fields.get("tender_fee"):
                    opp["tender_fee"] = fields["tender_fee"]
                if fields.get("emd_amount"):
                    opp["emd_amount"] = fields["emd_amount"]
                if fields.get("tender_category"):
                    opp["tender_category"] = fields["tender_category"]
                    opp["category_name"] = fields["tender_category"]
                if fields.get("product_category"):
                    opp["product_category"] = fields["product_category"]
                if fields.get("inviting_authority_name"):
                    opp["inviting_authority_name"] = fields["inviting_authority_name"]
                if fields.get("inviting_authority_address"):
                    opp["inviting_authority_address"] = fields["inviting_authority_address"]
                if docs:
                    opp["documents"] = docs

                # Update raw_content with complete enriched information
                extra_content = (
                    f"\n--- Detailed Specifications ---\n"
                    f"Work Description: {fields.get('work_description', opp.get('description'))}\n"
                    f"Tender Category: {fields.get('tender_category', 'N/A')}\n"
                    f"Product Category: {fields.get('product_category', 'N/A')}\n"
                    f"Tender Fee: {fields.get('tender_fee', 'N/A')}\n"
                    f"EMD Amount: {fields.get('emd_amount', 'N/A')}\n"
                    f"Location: {fields.get('location', opp.get('location'))}\n"
                    f"Pincode: {fields.get('pincode', 'N/A')}\n"
                    f"Inviting Authority: {fields.get('inviting_authority_name', 'N/A')}\n"
                    f"Address: {fields.get('inviting_authority_address', 'N/A')}\n"
                    f"Documents: {', '.join([d.get('url', '') for d in docs])}\n"
                )
                opp["raw_content"] += extra_content
                opp["raw_html"] = detail_html

            except Exception as e:
                logger.warning(f"Error enriching tender {opp.get('reference_number')}: {e}")

        # Execute with an active session (pacing requests gracefully)
        if client is not None:
            for opp in opportunities:
                await enrich_single(client, opp)
                await asyncio.sleep(0.5)
        else:
            try:
                import httpx
                transport = httpx.AsyncHTTPTransport(retries=3, verify=False)
                async with httpx.AsyncClient(transport=transport, headers=headers, timeout=35.0, follow_redirects=True) as local_client:
                    # Prime the session by visiting the list URL
                    await local_client.get(list_url)
                    for opp in opportunities:
                        await enrich_single(local_client, opp)
                        await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to create session for detail enrichment: {e}")

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str or date_str in ["--", "NA", "N/A"]:
            return None
        try:
            dt = date_parser.parse(date_str, fuzzy=True)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def _extract_location(self, title: str, org: str) -> Optional[str]:
        # Quick heuristic for common Indian cities/states in title or org
        text = f"{title} {org}".upper()
        common_places = [
            "SRINAGAR", "PALAKKAD", "COIMBATORE", "BARAUNI", "JAMUI", "LUCKNOW", "DELHI",
            "MUMBAI", "KOLKATA", "CHENNAI", "BANGALORE", "HYDERABAD", "AHMEDABAD",
            "PUNE", "NAGPUR", "BHOPAL", "PATNA", "RANCHI", "GUWAHATI", "DEHRADUN"
        ]
        for place in common_places:
            if re.search(r"\b" + place + r"\b", text):
                return place.title()
        return None
