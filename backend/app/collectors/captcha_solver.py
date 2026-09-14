import asyncio
import logging
from urllib.parse import urljoin
from typing import Optional, Tuple, Dict, Any, List
import httpx
from bs4 import BeautifulSoup
import ddddocr

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """
    Automated CAPTCHA solver and detail page parser for CPPP (eprocure.gov.in).
    Uses ddddocr to solve image captchas and extracts structured tender details,
    specifications, and document download links.
    """

    _ocr = None

    @classmethod
    def get_ocr(cls) -> ddddocr.DdddOcr:
        if cls._ocr is None:
            # Initialize ddddocr ONNX model once
            cls._ocr = ddddocr.DdddOcr(show_ad=False)
        return cls._ocr

    @classmethod
    async def solve_and_fetch_detail(
        cls,
        client: httpx.AsyncClient,
        detail_url: str,
        list_url: str,
        max_retries: int = 3
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Navigates to detail_url within the active session, detects CAPTCHA,
        downloads and solves the CAPTCHA image using OCR, and submits the form.
        Returns (html_content, error_message).
        """
        ocr = cls.get_ocr()

        # Clean detail URL if relative
        if detail_url.startswith("/"):
            detail_url = f"https://eprocure.gov.in{detail_url}"

        try:
            r = await client.get(detail_url, headers={"Referer": list_url})
            if r.status_code != 200:
                return None, f"HTTP status {r.status_code} fetching detail page"
            current_html = r.text
        except Exception as e:
            return None, f"Connection error fetching detail URL: {str(e)}"

        # Check if page is already resolved or if a captcha form is present
        soup = BeautifulSoup(current_html, "html.parser")
        form = soup.find("form", id=lambda x: x and "tender" in x.lower()) or soup.find("form")
        if not form or "tenderfullview-tenders" not in (form.get("id") or ""):
            # No captcha required or already bypassed
            return current_html, None

        # Solve captcha loop
        for attempt in range(max_retries):
            det_soup = BeautifulSoup(current_html, "html.parser")
            form = det_soup.find("form", id=lambda x: x and "tender" in x.lower()) or det_soup.find("form")
            if not form or "tenderfullview-tenders" not in (form.get("id") or ""):
                logger.info(f"Detail page unlocked on attempt {attempt + 1}!")
                return current_html, None

            captcha_img = det_soup.find("img", src=lambda s: s and "captcha" in s.lower())
            if not captcha_img:
                logger.warning("No captcha image found on page, returning current content.")
                return current_html, None

            img_src = captcha_img.get("src", "")
            img_url = f"https://eprocure.gov.in{img_src}" if img_src.startswith("/") else img_src

            try:
                img_resp = await client.get(img_url, headers={"Referer": detail_url})
                if img_resp.status_code != 200:
                    await asyncio.sleep(1)
                    continue

                # Run OCR
                raw_code = ocr.classification(img_resp.content)
                code = raw_code.strip().replace(" ", "")
                logger.info(f"CPPP Captcha attempt {attempt + 1}: Solved '{code}'")

                # Prepare form data
                form_data = {}
                for inp in form.find_all("input"):
                    n = inp.get("name")
                    v = inp.get("value", "")
                    if n:
                        form_data[n] = v
                form_data["captcha_response"] = code
                form_data["op"] = "Submit"

                action = form.get("action") or detail_url
                post_url = f"https://eprocure.gov.in{action}" if action.startswith("/") else action

                post_resp = await client.post(post_url, data=form_data, headers={"Referer": detail_url})
                if post_resp.status_code == 200:
                    current_html = post_resp.text
                    if "tenderfullview-tenders" not in current_html and (
                        "Work Description" in current_html or "Tender Fee" in current_html or "Organisation Chain" in current_html
                    ):
                        logger.info(f"Successfully bypassed CPPP captcha on attempt {attempt + 1}")
                        return current_html, None
                    else:
                        logger.warning(f"Captcha incorrect or page reloaded, retrying ({attempt + 1}/{max_retries})")
                        await asyncio.sleep(0.8)
            except Exception as e:
                logger.warning(f"Captcha solve attempt {attempt + 1} failed with error: {e}")
                await asyncio.sleep(0.8)

        # Check if final HTML contains details
        if "Work Description" in current_html or "Organisation Chain" in current_html:
            return current_html, None

        return current_html, "Failed to bypass captcha after retries"

    @classmethod
    def parse_cppp_detail_html(cls, html: str, base_url: Optional[str] = "https://eprocure.gov.in") -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
        """
        Parses structured tender detail fields and document links from the unlocked detail HTML.
        Returns (extracted_fields_dict, documents_list).
        """
        if not html:
            return {}, []

        soup = BeautifulSoup(html, "html.parser")
        raw_fields: Dict[str, str] = {}
        documents: List[Dict[str, str]] = []
        base = base_url or "https://eprocure.gov.in"

        # 1. Parse table rows with key-value pairs
        for tr in soup.find_all("tr"):
            # Check document links in this row
            for a in tr.find_all("a", href=True):
                href = a["href"].strip()
                title = a.get_text(strip=True) or a.get("title", "").strip() or "Tender Document"
                if href and ("tendersfullview" not in href) and ("javascript:" not in href) and not href.startswith("#"):
                    full_href = urljoin(base, href)
                    # Filter out generic header links like "Skip to Main Content"
                    if not any(ign in title.lower() for ign in ["skip to", "screen reader", "about us", "home", "faq"]):
                        if not any(d["url"] == full_href for d in documents):
                            documents.append({"title": title, "url": full_href})

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

        # 2. Extract structured attributes
        enriched: Dict[str, Any] = {}

        # Organisation
        org_chain = raw_fields.get("Organisation Chain") or raw_fields.get("Organisation Name")
        if org_chain:
            enriched["organization"] = org_chain

        org_type = raw_fields.get("Organisation Type")
        if org_type:
            enriched["organization_type"] = org_type

        # Work Description
        work_desc = raw_fields.get("Work Description") or raw_fields.get("Tender Title")
        if work_desc:
            enriched["work_description"] = work_desc

        # Location & Pincode
        loc = raw_fields.get("Location")
        if loc and loc.strip() and loc.strip() not in ["--", "NA", "N/A"]:
            enriched["location"] = loc.strip()

        pincode = raw_fields.get("Pincode")
        if pincode and pincode.strip() and pincode.strip() not in ["--", "NA", "N/A"]:
            enriched["pincode"] = pincode.strip()

        # Tender Category & Product Category
        tender_cat = raw_fields.get("Tender Category")
        if tender_cat:
            enriched["tender_category"] = tender_cat

        prod_cat = raw_fields.get("Product Category")
        if prod_cat:
            enriched["product_category"] = prod_cat

        # Fees
        fee_val = raw_fields.get("Tender Fee in ₹") or raw_fields.get("Tender Fee")
        if fee_val and fee_val.strip() not in ["--", "NA"]:
            enriched["tender_fee"] = fee_val.strip()

        emd_val = raw_fields.get("EMD Amount in ₹") or raw_fields.get("EMD Amount") or raw_fields.get("EMD")
        if emd_val and emd_val.strip() not in ["--", "NA"]:
            enriched["emd_amount"] = emd_val.strip()
            # If tender value was empty, EMD often gives a lower bound estimate or can be stored
            try:
                numeric_emd = float(emd_val.replace(",", "").strip())
                if numeric_emd > 0:
                    enriched["emd_numeric"] = numeric_emd
            except Exception:
                pass

        # Tender Inviting Authority
        tia_name = raw_fields.get("Name")
        tia_addr = raw_fields.get("Address")
        if tia_name and tia_name.strip() not in ["--", "NA"]:
            enriched["inviting_authority_name"] = tia_name.strip()
        if tia_addr and tia_addr.strip() not in ["--", "NA"]:
            enriched["inviting_authority_address"] = tia_addr.strip()

        # Pre-qualification / Requirements
        pre_qual = raw_fields.get("Pre Qualification Details")
        if pre_qual and pre_qual.strip() not in ["--", "NA"]:
            enriched["requirements"] = [pre_qual.strip()]

        return enriched, documents

