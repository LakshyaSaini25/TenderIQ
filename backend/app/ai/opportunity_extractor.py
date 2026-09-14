import json
import re
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError

from app.ai.ollama_client import OllamaClient
from app.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT_EXTRACTION, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class AIExtractionOutput(BaseModel):
    """
    Pydantic schema to strictly validate structured JSON returned by Ollama.
    """
    is_opportunity: bool = True
    type: Optional[str] = "TENDER"
    title: Optional[str] = None
    reference_number: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    value: Optional[Union[float, int, str]] = None
    currency: Optional[str] = None
    published_at: Optional[str] = None
    deadline: Optional[str] = None
    eligibility: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    experience_requirements: List[str] = Field(default_factory=list)
    equipment_requirements: List[str] = Field(default_factory=list)
    contacts: Optional[Dict[str, List[str]]] = Field(default_factory=lambda: {"emails": [], "phones": []})


class OpportunityAIExtractor:
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    async def extract(
        self,
        content_doc: Dict[str, Any],
        deterministic_opp: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Public entry point called by OpportunityService.
        Runs extract_and_merge() and returns a normalized result dict:
        {
          "status": "SUCCESS" | "UNAVAILABLE" | "FAILED",
          "model": str,
          "prompt_version": str,
          "enriched_fields": {field: value, ...},   # only AI-enriched fields
          "error": str | None
        }
        """
        result = await self.extract_and_merge(content_doc, deterministic_opp)
        merged = result.get("merged_opportunity", {})

        if result.get("success"):
            # Collect the fields that AI actually contributed
            det = deterministic_opp or {}
            ai_only_fields = [
                "eligibility", "requirements", "scope", "certifications",
                "experience_requirements", "equipment_requirements", "ai",
                "description", "organization", "department", "location"
            ]
            enriched = {}
            for field in ai_only_fields:
                new_val = merged.get(field)
                old_val = det.get(field)
                if new_val and new_val != old_val:
                    enriched[field] = new_val

            return {
                "status": "SUCCESS",
                "model": self.client.default_model,
                "prompt_version": PROMPT_VERSION,
                "enriched_fields": enriched,
                "error": None
            }
        else:
            error_type = result.get("error_type", "")
            ai_status = "UNAVAILABLE" if error_type == "unavailable" else "FAILED"
            return {
                "status": ai_status,
                "model": self.client.default_model,
                "prompt_version": PROMPT_VERSION,
                "enriched_fields": {},
                "error": result.get("error")
            }

    async def extract_and_merge(
        self,
        content_doc: Dict[str, Any],
        deterministic_opp: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes Ollama AI extraction, validates structured output, and executes
        hybrid merge where deterministic high-confidence extraction takes precedence.
        """
        title = content_doc.get("title", "")
        url = content_doc.get("url", "")
        raw_content = content_doc.get("content", "")

        # Limit content to 5000 characters for optimal inference speed & context fit
        clipped_content = raw_content[:5000] if raw_content else ""

        prompt = USER_PROMPT_TEMPLATE.format(
            title=title,
            url=url,
            content=clipped_content
        )

        gen_result = await self.client.generate(
            prompt=prompt,
            system=SYSTEM_PROMPT_EXTRACTION,
            format="json"
        )

        if not gen_result.get("success"):
            logger.warning(f"Ollama AI extraction failed: {gen_result.get('error')}")
            # Fallback gracefully to deterministic result with AI failed metadata
            merged = dict(deterministic_opp or {})
            merged["ai"] = {
                "processed": False,
                "model": self.client.default_model,
                "prompt_version": PROMPT_VERSION,
                "processed_at": datetime.now(timezone.utc),
                "error": gen_result.get("error")
            }
            return {
                "success": False,
                "error": gen_result.get("error"),
                "error_type": gen_result.get("error_type"),
                "merged_opportunity": merged
            }

        raw_text = gen_result.get("response", "")
        parsed_ai_data, parse_err = self._parse_json_safely(raw_text)

        if parse_err or not parsed_ai_data:
            logger.error(f"Failed to parse Ollama JSON response: {parse_err}")
            merged = dict(deterministic_opp or {})
            merged["ai"] = {
                "processed": False,
                "model": self.client.default_model,
                "prompt_version": PROMPT_VERSION,
                "processed_at": datetime.now(timezone.utc),
                "error": f"JSON parse error: {parse_err}"
            }
            return {
                "success": False,
                "error": f"Invalid JSON from AI model: {parse_err}",
                "error_type": "json_parse_error",
                "merged_opportunity": merged
            }

        # Validate with Pydantic
        try:
            validated_ai = AIExtractionOutput.model_validate(parsed_ai_data)
        except ValidationError as val_err:
            logger.error(f"Pydantic validation failed for AI output: {val_err}")
            merged = dict(deterministic_opp or {})
            merged["ai"] = {
                "processed": False,
                "model": self.client.default_model,
                "prompt_version": PROMPT_VERSION,
                "processed_at": datetime.now(timezone.utc),
                "error": f"Validation error: {val_err.errors()[0].get('msg')}"
            }
            return {
                "success": False,
                "error": f"AI output schema validation error: {val_err.errors()[0].get('msg')}",
                "error_type": "validation_error",
                "merged_opportunity": merged
            }

        # Perform Hybrid Merge
        merged_opp = self._merge_deterministic_and_ai(
            content_doc=content_doc,
            deterministic_opp=deterministic_opp or {},
            ai_data=validated_ai.model_dump()
        )

        return {
            "success": True,
            "merged_opportunity": merged_opp,
            "duration": gen_result.get("duration")
        }

    def _merge_deterministic_and_ai(
        self,
        content_doc: Dict[str, Any],
        deterministic_opp: Dict[str, Any],
        ai_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merges deterministic extraction with AI output.
        Deterministic high-confidence values (reference number, value, deadline, contacts)
        always override AI output to prevent hallucinations.
        """
        merged = dict(deterministic_opp)

        # Baseline IDs and URLs
        merged["source_id"] = deterministic_opp.get("source_id") or content_doc.get("source_id")
        merged["content_id"] = deterministic_opp.get("content_id") or str(content_doc.get("_id", ""))
        merged["source_url"] = deterministic_opp.get("source_url") or content_doc.get("url")

        # Opportunity identification:
        # If deterministic already said True or AI says True, mark True
        merged["is_opportunity"] = deterministic_opp.get("is_opportunity", False) or ai_data.get("is_opportunity", True)

        # Opportunity Type: prefer deterministic if confident, else use AI
        det_type = deterministic_opp.get("type")
        if det_type and det_type != "OTHER":
            merged["type"] = det_type
        else:
            merged["type"] = ai_data.get("type") or "TENDER"

        # Title
        merged["title"] = deterministic_opp.get("title") or ai_data.get("title") or content_doc.get("title") or "Opportunity"

        # Reference Number: Deterministic wins!
        if not merged.get("reference_number") and ai_data.get("reference_number"):
            merged["reference_number"] = ai_data.get("reference_number")

        # Organization & Department: Deterministic wins, fallback to AI
        if not merged.get("organization") and ai_data.get("organization"):
            merged["organization"] = ai_data.get("organization")
        if not merged.get("department") and ai_data.get("department"):
            merged["department"] = ai_data.get("department")

        # Location: Deterministic wins, fallback to AI
        if not merged.get("location") and ai_data.get("location"):
            merged["location"] = ai_data.get("location")

        # Description: Use AI concise summary if present, else fallback to deterministic/raw
        if ai_data.get("description"):
            merged["description"] = ai_data.get("description")
        elif not merged.get("description"):
            merged["description"] = content_doc.get("content", "")[:1000]

        # Financial Value: Deterministic strictly wins to prevent AI math hallucination
        if merged.get("value") is None and ai_data.get("value") is not None:
            raw_val = ai_data.get("value")
            try:
                merged["value"] = float(raw_val)
            except (ValueError, TypeError):
                merged["value"] = raw_val
        if not merged.get("currency") and ai_data.get("currency"):
            merged["currency"] = ai_data.get("currency")

        # Deadline & Published Date: Deterministic strictly wins
        if not merged.get("deadline") and ai_data.get("deadline"):
            try:
                from dateutil import parser as dt_parser
                parsed_dl = dt_parser.parse(ai_data["deadline"]).replace(tzinfo=timezone.utc)
                merged["deadline"] = parsed_dl
            except Exception:
                pass

        if not merged.get("published_at") and ai_data.get("published_at"):
            try:
                from dateutil import parser as dt_parser
                parsed_pb = dt_parser.parse(ai_data["published_at"]).replace(tzinfo=timezone.utc)
                merged["published_at"] = parsed_pb
            except Exception:
                pass

        # Contacts: Merge emails and phones
        contacts = merged.get("contacts") or {"emails": [], "phones": []}
        ai_contacts = ai_data.get("contacts") or {}
        emails = list(set(contacts.get("emails", []) + ai_contacts.get("emails", [])))
        phones = list(set(contacts.get("phones", []) + ai_contacts.get("phones", [])))
        merged["contacts"] = {"emails": emails, "phones": phones}

        # Rich AI-only Fields
        merged["eligibility"] = ai_data.get("eligibility", [])
        merged["requirements"] = ai_data.get("requirements", [])
        merged["scope"] = ai_data.get("scope", [])
        merged["certifications"] = ai_data.get("certifications", [])
        merged["experience_requirements"] = ai_data.get("experience_requirements", [])
        merged["equipment_requirements"] = ai_data.get("equipment_requirements", [])

        # AI Metadata
        merged["ai"] = {
            "processed": True,
            "model": self.client.default_model,
            "prompt_version": PROMPT_VERSION,
            "processed_at": datetime.now(timezone.utc),
            "confidence": None
        }

        # Status
        deadline = merged.get("deadline")
        if deadline and isinstance(deadline, datetime) and deadline < datetime.now(timezone.utc):
            merged["status"] = "CLOSED"
        elif not merged.get("status"):
            merged["status"] = "OPEN"

        return merged

    def _parse_json_safely(self, text: str) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Parses JSON from raw model string, stripping potential markdown blocks.
        """
        clean_text = text.strip()
        # Remove ```json ... ``` wrapper if present
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)

        # Match outer braces if model included extra preamble
        match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(1)

        try:
            data = json.loads(clean_text)
            if isinstance(data, dict):
                return data, None
            return None, "Root element is not a JSON object"
        except json.JSONDecodeError as e:
            return None, str(e)

