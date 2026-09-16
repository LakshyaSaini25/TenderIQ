import logging
import re
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime, timezone
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.source_repository import SourceRepository

logger = logging.getLogger(__name__)

TENDER247_HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "origin": "https://www.tender247.com",
    "referer": "https://www.tender247.com/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}

AI_SEARCH_URL = "https://www.tender247.com/apigateway/aisearch/tender_ai_search"
SEARCH_TENDER_URL = "https://www.tender247.com/apigateway/T247Tender/api/tender/search-tender"
COUNT_TENDER_URL = "https://www.tender247.com/apigateway/T247Tender/api/tender/tender-search-count"
STATE_ALL_URL = "https://www.tender247.com/apigateway/T247Tender/api/usermaster/common/state-getall"
CITY_ALL_URL = "https://www.tender247.com/apigateway/T247Tender/api/usermaster/common/city-getall"


def clean_search_text(text: str) -> str:
    """
    Cleans search_text by stripping symbols like &, /, -, +, *, @, etc.
    which cause Postgres tsquery syntax errors on the upstream portal.
    """
    if not text:
        return ""
    # Replace symbols and punctuation with space
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    # Collapse multiple whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


class ExploreService:
    def __init__(self):
        self.opportunity_repo = OpportunityRepository()
        self.source_repo = SourceRepository()

    async def get_states(self) -> List[Dict[str, Any]]:
        """
        Retrieves all states with state_id and state_name from the portal.
        """
        body = {"id": 0, "parentids": ""}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(STATE_ALL_URL, json=body, headers=TENDER247_HEADERS)
                if resp.status_code == 200:
                    data = resp.json().get("Data", [])
                    # Sort alphabetically
                    data.sort(key=lambda x: x.get("state_name", ""))
                    return data
            except Exception as e:
                logger.error(f"Error fetching states: {e}")
        return []

    async def get_cities(self, state_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all cities belonging to a state.
        """
        if not state_id:
            return []
        body = {
            "id": 0,
            "parentids": str(state_id),
            "statezoneid": "",
            "noofrecords": 500,
            "pageNo": 1,
            "name": ""
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(CITY_ALL_URL, json=body, headers=TENDER247_HEADERS)
                if resp.status_code == 200:
                    data = resp.json().get("Data", [])
                    data.sort(key=lambda x: x.get("city_name", ""))
                    return data
            except Exception as e:
                logger.error(f"Error fetching cities for state {state_id}: {e}")
        return []

    async def ai_search(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calls the AI Search API to parse natural language queries
        into a structured search payload.
        """
        body = {
            "query": query,
            "variables": variables or {}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(AI_SEARCH_URL, json=body, headers=TENDER247_HEADERS)
            if resp.status_code != 200:
                logger.error(f"AI Search returned {resp.status_code}: {resp.text}")
                return {"status": "error", "message": f"AI search failed with status {resp.status_code}", "data": None}
            return resp.json()

    async def search_tenders(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Searches tenders.
        Robust fallback strategy:
        1. Try requested payload (with cleaned search_text if present)
        2. If fails or search_by == 2 yields no results, try with search_by = 0
        3. If still fails (e.g. tsquery syntax error on compound words), try with first word of search_text
        4. If still fails, try with search_text = "" so user gets default tenders
        """
        # Ensure search_text is cleaned of dangerous symbols
        original_search_text = payload.get("search_text", "")
        cleaned_text = clean_search_text(original_search_text)

        working_payload = dict(payload)
        working_payload["search_text"] = cleaned_text

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Attempt 1: As requested with cleaned text
            try:
                resp = await client.post(SEARCH_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                resp_json = resp.json() if resp.status_code == 200 else {}
            except Exception as e:
                logger.warning(f"Search attempt 1 failed: {e}")
                resp_json = {}

            # Check if Attempt 2 (search_by = 0) is needed
            if not resp_json.get("Success") or not resp_json.get("Data"):
                logger.info("Attempting fallback with search_by = 0")
                working_payload["search_by"] = 0
                try:
                    resp2 = await client.post(SEARCH_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                    if resp2.status_code == 200 and resp2.json().get("Success"):
                        res2_json = resp2.json()
                        res2_json["used_search_by"] = 0
                        return res2_json
                except Exception as e2:
                    logger.warning(f"Search attempt 2 failed: {e2}")

            # Check if Attempt 3 (single core keyword) is needed if search_text has multiple words
            if (not resp_json.get("Success") or not resp_json.get("Data")) and len(cleaned_text.split()) > 1:
                first_keyword = cleaned_text.split()[0]
                logger.info(f"Attempting fallback with first keyword: '{first_keyword}'")
                working_payload["search_text"] = first_keyword
                working_payload["search_by"] = 0
                try:
                    resp3 = await client.post(SEARCH_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                    if resp3.status_code == 200 and resp3.json().get("Success"):
                        res3_json = resp3.json()
                        res3_json["used_search_by"] = 0
                        return res3_json
                except Exception as e3:
                    logger.warning(f"Search attempt 3 failed: {e3}")

            # Check if Attempt 4 (blank search_text) is needed
            if not resp_json.get("Success") and cleaned_text:
                logger.info("Attempting fallback with empty search_text")
                working_payload["search_text"] = ""
                working_payload["search_by"] = 0
                try:
                    resp4 = await client.post(SEARCH_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                    if resp4.status_code == 200 and resp4.json().get("Success"):
                        res4_json = resp4.json()
                        res4_json["used_search_by"] = 0
                        return res4_json
                except Exception as e4:
                    logger.warning(f"Search attempt 4 failed: {e4}")

            return resp_json

    async def count_tenders(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gets total tender count matching the search criteria with fallback handling.
        """
        cleaned_text = clean_search_text(payload.get("search_text", ""))
        working_payload = dict(payload)
        working_payload["search_text"] = cleaned_text

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(COUNT_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                resp_json = resp.json() if resp.status_code == 200 else {}
                if resp_json.get("Success"):
                    return resp_json
            except Exception as e:
                logger.warning(f"Count attempt 1 failed: {e}")

            # Fallback 1: search_by = 0
            working_payload["search_by"] = 0
            try:
                resp2 = await client.post(COUNT_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                if resp2.status_code == 200 and resp2.json().get("Success"):
                    return resp2.json()
            except Exception:
                pass

            # Fallback 2: first keyword
            if len(cleaned_text.split()) > 1:
                working_payload["search_text"] = cleaned_text.split()[0]
                try:
                    resp3 = await client.post(COUNT_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                    if resp3.status_code == 200 and resp3.json().get("Success"):
                        return resp3.json()
                except Exception:
                    pass

            # Fallback 3: empty search_text
            working_payload["search_text"] = ""
            try:
                resp4 = await client.post(COUNT_TENDER_URL, json=working_payload, headers=TENDER247_HEADERS)
                if resp4.status_code == 200 and resp4.json().get("Success"):
                    return resp4.json()
            except Exception:
                pass

        return {"Success": False, "Data": [{"tendercount": 0}]}

    async def import_tender_to_opportunities(self, tender_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Imports an explored tender into TenderMate's local Opportunities collection.
        """
        # Ensure a default 'National Tender Network' source exists in the DB
        sources = await self.source_repo.get_all()
        target_source = next((s for s in sources if "national tender" in s.get("name", "").lower() or "aggregator" in s.get("name", "").lower()), None)
        if not target_source:
            created_src = await self.source_repo.create({
                "name": "National Tender Aggregator",
                "url": "https://eprocure.gov.in",
                "type": "TENDER_PORTAL",
                "crawl_frequency": "WEEKLY",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
            source_id = str(created_src.get("_id") or created_src.get("id"))
        else:
            source_id = str(target_source.get("_id") or target_source.get("id"))

        tender_id = tender_data.get("tender_id")
        title = tender_data.get("requirement_workbrief") or f"Tender #{tender_id}"
        estimated_cost = tender_data.get("estimatedcost")
        emd = tender_data.get("earnest_money_deposite")
        location = tender_data.get("site_location") or "India"
        org = tender_data.get("organization_name") or "Government Authority"
        if org.strip().lower() == "sss":
            org = "Public Sector Organization"
        deadline_str = tender_data.get("tender_endsubmission_datetime") or ""

        # Parse deadline if formatted as DD-MM-YYYY
        deadline_dt = None
        if deadline_str:
            try:
                deadline_dt = datetime.strptime(deadline_str.strip(), "%d-%m-%Y").replace(tzinfo=timezone.utc)
            except Exception:
                pass

        opp_doc = {
            "source_id": source_id,
            "type": "TENDER",
            "title": title.title(),
            "reference_number": f"TDR-{tender_id}",
            "description": title,
            "organization": org,
            "location": location,
            "value": estimated_cost,
            "emd_amount": str(emd) if emd else None,
            "deadline": deadline_dt,
            "source_url": "https://eprocure.gov.in",
            "status": "OPEN",
            "is_opportunity": True,
            "detection_reason": "Imported from Live Explore Tenders",
            "detail_solved": True,
            "detail_enriching": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        # Save to database using OpportunityRepository
        created = await self.opportunity_repo.create(opp_doc)
        return {
            "success": True,
            "message": f"Successfully imported Tender #{tender_id} to Opportunities",
            "opportunity_id": str(created.get("_id") or created.get("id"))
        }
