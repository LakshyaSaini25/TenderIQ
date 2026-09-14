import re
from typing import Dict, Any, Tuple
from app.processors.rules import (
    TENDER_KEYWORDS,
    PROJECT_KEYWORDS,
    PROCUREMENT_KEYWORDS,
    CONSULTANCY_KEYWORDS,
    NON_OPPORTUNITY_INDICATORS
)

class Classifier:
    @staticmethod
    def classify(title: str, text: str) -> Tuple[bool, str, str]:
        """
        Determines whether text content is an opportunity, classifies its type,
        and provides an explainable detection reason.

        Returns: (is_opportunity: bool, opportunity_type: str, detection_reason: str)
        """
        title = title or ""
        text = text or ""
        combined = f"{title}\n{text}".lower()

        # Check non-opportunity indicators first for short texts
        if len(combined.strip()) < 30:
            return False, "OTHER", "Content too short to be an opportunity"

        # Check explicit exclusions if no strong opportunity keywords exist
        non_opp_matches = [kw for kw in NON_OPPORTUNITY_INDICATORS if kw in combined]
        
        # Match keywords by word boundaries or phrase match
        tender_matches = [kw for kw in TENDER_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', combined)]
        project_matches = [kw for kw in PROJECT_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', combined)]
        procurement_matches = [kw for kw in PROCUREMENT_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', combined)]
        consultancy_matches = [kw for kw in CONSULTANCY_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', combined)]

        total_matches = len(tender_matches) + len(project_matches) + len(procurement_matches) + len(consultancy_matches)

        if total_matches == 0:
            if non_opp_matches:
                return False, "OTHER", f"Matched non-opportunity indicators: {', '.join(non_opp_matches[:2])}"
            return False, "OTHER", "No opportunity keywords detected"

        # Determine type based on dominant keyword matches
        if len(tender_matches) >= max(len(project_matches), len(procurement_matches), len(consultancy_matches)):
            opp_type = "TENDER"
            reason = f"Matched tender keywords: {', '.join(tender_matches[:3])}"
        elif len(procurement_matches) > len(project_matches):
            opp_type = "PROCUREMENT"
            reason = f"Matched procurement keywords: {', '.join(procurement_matches[:3])}"
        elif len(project_matches) > 0:
            opp_type = "PROJECT"
            reason = f"Matched project keywords: {', '.join(project_matches[:3])}"
        else:
            opp_type = "TENDER"
            reason = f"Matched opportunity keywords: {', '.join((tender_matches + consultancy_matches)[:3])}"

        return True, opp_type, reason

