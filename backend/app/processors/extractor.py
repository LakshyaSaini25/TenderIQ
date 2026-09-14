import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

class Extractor:

    @staticmethod
    def extract_reference_number(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts reference/tender number from text.
        Returns tuple: (normalized_ref_number, raw_ref_number)
        """
        if not text:
            return None, None

        patterns = [
            r"(?:Tender\s*(?:Ref|ID|No|Num|Number|Code)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})",
            r"(?:Reference\s*(?:No|Num|Number|Code)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})",
            r"(?:Ref\s*(?:No|Num|Number|Code)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})",
            r"(?:NIT\s*(?:No|Num|Number|Code)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})",
            r"(?:RFP\s*(?:No|Num|Number|Code)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})",
            r"(?:RFQ\s*(?:No|Num|Number|Code)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})",
            r"(?:Bid\s*(?:No|Num|Number|ID)[\.\s:=#—–\-]+)([A-Za-z0-9/\-_]{4,40})"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_ref = match.group(0).strip()
                extracted = match.group(1).strip()
                # Clean up trailing punctuation
                extracted = re.sub(r'[\.,;:]+$', '', extracted)
                if len(extracted) >= 3 and not re.match(r'^\d+$', extracted) or len(extracted) >= 5:
                    return extracted, raw_ref

        return None, None

    @staticmethod
    def extract_deadline(text: str) -> Optional[datetime]:
        """
        Extracts deadline / closing date from text.
        """
        if not text:
            return None

        deadline_patterns = [
            r"(?:Closing\s*Date|Submission\s*Deadline|Bid\s*Submission\s*End\s*Date|Last\s*Date|Due\s*Date|End\s*Date)[\s:=]+([A-Za-z0-9\s,\-:\.\/]{6,30})"
        ]

        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_date_str = match.group(1).strip()
                dt = Extractor._parse_date_string(raw_date_str)
                if dt:
                    return dt
        return None

    @staticmethod
    def extract_published_date(text: str) -> Optional[datetime]:
        """
        Extracts published / issue date from text.
        """
        if not text:
            return None

        pub_patterns = [
            r"(?:Published\s*Date|Publish\s*Date|Start\s*Date|Date\s*of\s*Issue|Issue\s*Date)[\s:=]+([A-Za-z0-9\s,\-:\.\/]{6,30})"
        ]

        for pattern in pub_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_date_str = match.group(1).strip()
                dt = Extractor._parse_date_string(raw_date_str)
                if dt:
                    return dt
        return None

    @staticmethod
    def _parse_date_string(date_str: str) -> Optional[datetime]:
        """
        Helper method to parse date string using dateutil with fuzzy matching.
        """
        # Isolate potential date substring (first 25 chars or up to newline/comma)
        clean_str = re.split(r'[\r\n]', date_str)[0].strip()
        clean_str = clean_str[:30]

        try:
            dt = date_parser.parse(clean_str, fuzzy=True, dayfirst=True)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def extract_value(text: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """
        Extracts monetary value from text.
        Returns: (numeric_value: float | None, currency: str | None, value_text: str | None)
        """
        if not text:
            return None, None, None

        # Pattern matching e.g. "₹ 5,00,00,000", "Rs. 5 crore", "INR 10 lakh", "₹50 lakh", "₹2.5 crore", "$500,000"
        patterns = [
            r"((?:₹|Rs\.?|INR|\$|USD)\s*[\d,]+(?:\.\d+)?\s*(?:Crore|Crores|Cr|Lakh|Lakhs|L|Million|M|Billion|B)?)",
            r"([\d,]+(?:\.\d+)?\s*(?:Crore|Crores|Cr|Lakh|Lakhs|L)\s*(?:Rupees|INR|₹)?)"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_text = match.group(1).strip()
                numeric_val, currency = Extractor._parse_numeric_value(value_text)
                return numeric_val, currency, value_text

        return None, None, None

    @staticmethod
    def _parse_numeric_value(val_str: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Parses text like "₹5 Crore" or "Rs 10 Lakh" into numeric value and currency symbol/code.
        """
        currency = "INR" if any(c in val_str.upper() for c in ["₹", "RS", "INR"]) else "USD" if any(c in val_str.upper() for c in ["$", "USD"]) else None

        # Extract numerical digits & multipliers
        multiplier = 1.0
        val_upper = val_str.upper()

        if "CRORE" in val_upper or " CR" in val_upper or val_upper.endswith("CR") or "CRORES" in val_upper:
            multiplier = 10000000.0  # 1 Crore = 10,000,000
        elif "LAKH" in val_upper or " L" in val_upper or val_upper.endswith("L") or "LAKHS" in val_upper:
            multiplier = 100000.0    # 1 Lakh = 100,000
        elif "MILLION" in val_upper or " M" in val_upper:
            multiplier = 1000000.0
        elif "BILLION" in val_upper or " B" in val_upper:
            multiplier = 1000000000.0

        # Extract digits string
        digits_match = re.search(r'([\d,]+(?:\.\d+)?)', val_str)
        if digits_match:
            try:
                num_part = float(digits_match.group(1).replace(',', ''))
                calculated = num_part * multiplier
                return calculated, currency
            except ValueError:
                pass

        return None, currency

    @staticmethod
    def extract_contacts(text: str) -> Dict[str, List[str]]:
        """
        Extracts public email addresses and phone numbers.
        """
        if not text:
            return {"emails": [], "phones": []}

        # Emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = list(set(re.findall(email_pattern, text)))

        # Phones (Basic regex for Indian & international phone numbers)
        phone_pattern = r'(?:\+?91[\-\s]?)?[6-9]\d{9}|\b0\d{2,4}[\-\s]?\d{6,8}\b'
        phones = list(set(re.findall(phone_pattern, text)))

        return {
            "emails": emails[:5],   # Limit to top 5 contacts
            "phones": phones[:5]
        }

    @staticmethod
    def extract_organization(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts Organization and Department.
        Returns: (organization, department)
        """
        if not text:
            return None, None

        org = None
        dept = None

        org_match = re.search(r"(?:Organisation|Organization|Authority|Client|Issuer)[\s:=]+([A-Za-z0-9\s,\.\-]{3,60})", text, re.IGNORECASE)
        if org_match:
            org = org_match.group(1).strip()
            org = re.split(r'[\r\n]', org)[0].strip()

        dept_match = re.search(r"(?:Department|Dept)[\s:=]+([A-Za-z0-9\s,\.\-]{3,60})", text, re.IGNORECASE)
        if dept_match:
            dept = dept_match.group(1).strip()
            dept = re.split(r'[\r\n]', dept)[0].strip()

        return org, dept

    @staticmethod
    def extract_location(text: str) -> Optional[str]:
        """
        Extracts Location from text.
        """
        if not text:
            return None

        loc_match = re.search(r"(?:Location|State|City|Work Location|Place)[\s:=]+([A-Za-z0-9\s,\-]{3,40})", text, re.IGNORECASE)
        if loc_match:
            loc = loc_match.group(1).strip()
            return re.split(r'[\r\n]', loc)[0].strip()

        return None
