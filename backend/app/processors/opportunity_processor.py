import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from app.processors.classifier import Classifier
from app.processors.extractor import Extractor

logger = logging.getLogger(__name__)

class OpportunityProcessor:

    @staticmethod
    def process(content_doc: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Processes a content document to detect if it is an opportunity,
        extracts structured fields deterministically, and returns standard opportunity data.

        Returns: (is_opportunity: bool, status_reason: str, opportunity_dict: Optional[dict])
        """
        title = content_doc.get("title", "")
        text = content_doc.get("content", "")
        url = content_doc.get("url", "")
        source_id = content_doc.get("source_id", "")
        content_id = str(content_doc.get("_id", ""))

        # 1. Classification
        is_opp, opp_type, detection_reason = Classifier.classify(title, text)

        if not is_opp:
            return False, "NOT_AN_OPPORTUNITY", None

        # 2. Field Extractions
        combined_text = f"{title}\n\n{text}"

        ref_num, ref_raw = Extractor.extract_reference_number(combined_text)
        pub_date = Extractor.extract_published_date(combined_text)
        deadline = Extractor.extract_deadline(combined_text)
        numeric_val, currency, value_text = Extractor.extract_value(combined_text)
        contacts = Extractor.extract_contacts(combined_text)
        org, dept = Extractor.extract_organization(combined_text)
        loc = Extractor.extract_location(combined_text)

        # Status determination
        status = "OPEN"
        if deadline and deadline < datetime.now(timezone.utc):
            status = "CLOSED"

        # Build Opportunity Document
        opportunity_data = {
            "source_id": source_id,
            "content_id": content_id,
            "type": opp_type,
            "title": title or f"Opportunity from {url}",
            "description": text[:2000] if text else None,
            "reference_number": ref_num,
            "reference_number_raw": ref_raw,
            "organization": org,
            "department": dept,
            "location": loc,
            "category_id": None,
            "category_name": None,
            "value": numeric_val,
            "currency": currency,
            "value_text": value_text,
            "published_at": pub_date or content_doc.get("first_seen_at"),
            "deadline": deadline,
            "contacts": contacts,
            "source_url": url,
            "status": status,
            "is_opportunity": True,
            "detection_reason": detection_reason
        }

        return True, "SUCCESS", opportunity_data

