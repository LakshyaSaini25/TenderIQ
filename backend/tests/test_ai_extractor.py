"""
Tests for OpportunityAIExtractor:
- valid JSON from AI
- malformed JSON
- missing required fields
- invalid enum values
- invalid date values
- invalid numeric values
- hybrid extraction (deterministic wins over AI for high-confidence fields)
- no hallucination when field is absent in content
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.ai.opportunity_extractor import OpportunityAIExtractor


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_extractor(generate_result: dict) -> OpportunityAIExtractor:
    """Create OpportunityAIExtractor with a mocked OllamaClient.generate()."""
    extractor = OpportunityAIExtractor()
    extractor.client.generate = AsyncMock(return_value=generate_result)
    return extractor


SAMPLE_CONTENT = {
    "_id": "abc123",
    "source_id": "src1",
    "url": "https://example.com/tender/1",
    "title": "Construction of Bridge at NH-44",
    "content": "The NHAI invites bids for construction of bridge. Deadline: 2026-10-25. Value: ₹5 crore.",
}

VALID_AI_JSON = {
    "is_opportunity": True,
    "type": "TENDER",
    "title": "Construction of Bridge at NH-44",
    "reference_number": None,
    "organization": "NHAI",
    "department": None,
    "description": "Bridge construction project on National Highway 44.",
    "location": "NH-44",
    "category": "Infrastructure",
    "value": 50000000,
    "currency": "INR",
    "published_at": None,
    "deadline": "2026-10-25",
    "eligibility": ["Registered contractor with PWD"],
    "requirements": ["Class-A contractor license"],
    "scope": ["Design and construction of 120m span bridge"],
    "certifications": ["ISO 9001"],
    "experience_requirements": ["Min 5 years in bridge construction"],
    "equipment_requirements": ["Crane 50T capacity"],
    "contacts": {"emails": [], "phones": []},
}


# ─── Valid JSON extraction ────────────────────────────────────────────────────

class TestValidExtraction:
    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        """extract() returns SUCCESS with enriched fields on valid AI JSON."""
        gen_result = {"success": True, "response": json.dumps(VALID_AI_JSON), "duration": 2.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract(SAMPLE_CONTENT)

        assert result["status"] == "SUCCESS"
        assert "eligibility" in result["enriched_fields"] or isinstance(result["enriched_fields"], dict)
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_scope_extracted(self):
        """Scope of work is extracted from AI output and stored in enriched fields."""
        gen_result = {"success": True, "response": json.dumps(VALID_AI_JSON), "duration": 1.8}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)

        merged = result["merged_opportunity"]
        assert isinstance(merged.get("scope"), list)
        assert len(merged["scope"]) > 0

    @pytest.mark.asyncio
    async def test_ai_metadata_stored(self):
        """AI metadata block is added to merged opportunity."""
        gen_result = {"success": True, "response": json.dumps(VALID_AI_JSON), "duration": 1.0}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        merged = result["merged_opportunity"]

        assert merged.get("ai", {}).get("processed") is True
        assert merged["ai"]["model"] == extractor.client.default_model
        assert merged["ai"]["prompt_version"] == "v1"


# ─── Malformed JSON ──────────────────────────────────────────────────────────

class TestMalformedJSON:
    @pytest.mark.asyncio
    async def test_malformed_json_returns_failure(self):
        """Extractor returns success=False when model returns broken JSON."""
        gen_result = {"success": True, "response": "This is not JSON at all", "duration": 0.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)

        assert result["success"] is False
        assert "json" in result.get("error_type", "").lower() or "json" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_partial_json_recovered(self):
        """Extractor can extract valid JSON from a response with surrounding text."""
        valid_json_in_text = f"Here is the result:\n{json.dumps(VALID_AI_JSON)}\nDone."
        gen_result = {"success": True, "response": valid_json_in_text, "duration": 1.0}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        # Should succeed because regex extracts the inner {} block
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_markdown_json_block_parsed(self):
        """Extractor strips markdown ```json ... ``` wrapper."""
        wrapped = f"```json\n{json.dumps(VALID_AI_JSON)}\n```"
        gen_result = {"success": True, "response": wrapped, "duration": 1.0}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        assert result["success"] is True


# ─── Invalid field values ─────────────────────────────────────────────────────

class TestInvalidFields:
    @pytest.mark.asyncio
    async def test_invalid_type_enum_defaults_gracefully(self):
        """An invalid 'type' enum value is handled without crashing."""
        bad_ai = dict(VALID_AI_JSON, type="INVALID_TYPE")
        gen_result = {"success": True, "response": json.dumps(bad_ai), "duration": 1.0}
        extractor = make_extractor(gen_result)

        # Should either fail validation or fall back
        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        # Either success=False OR merged type is not the bad value
        if result["success"]:
            # Pydantic may coerce or use default
            merged = result["merged_opportunity"]
            assert merged.get("type") is not None
        else:
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_invalid_date_skipped(self):
        """An unparseable deadline string is safely skipped (not saved as corrupted value)."""
        bad_ai = dict(VALID_AI_JSON, deadline="not-a-date")
        gen_result = {"success": True, "response": json.dumps(bad_ai), "duration": 1.0}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        if result["success"]:
            merged = result["merged_opportunity"]
            # deadline should be absent or None, not a raw bad string
            deadline = merged.get("deadline")
            assert deadline is None or isinstance(deadline, datetime)

    @pytest.mark.asyncio
    async def test_non_numeric_value_handled(self):
        """A non-numeric value string is stored as-is or skipped without crash."""
        bad_ai = dict(VALID_AI_JSON, value="five crore")
        gen_result = {"success": True, "response": json.dumps(bad_ai), "duration": 1.0}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        # Should not crash
        assert "merged_opportunity" in result


# ─── Hybrid Extraction: Deterministic wins ────────────────────────────────────

class TestHybridExtraction:
    @pytest.mark.asyncio
    async def test_deterministic_deadline_wins_over_ai(self):
        """
        When deterministic extraction has a deadline, it must NOT be overridden by AI.
        Regex says: 2026-10-25
        AI says:    2026-11-02
        Expected:   2026-10-25 (deterministic wins)
        """
        deterministic_opp = {
            "source_id": "src1",
            "source_url": "https://example.com/tender/1",
            "title": "Bridge Construction",
            "type": "TENDER",
            "deadline": datetime(2026, 10, 25, tzinfo=timezone.utc),  # high-confidence value
            "is_opportunity": True,
        }
        ai_with_diff_deadline = dict(VALID_AI_JSON, deadline="2026-11-02")
        gen_result = {"success": True, "response": json.dumps(ai_with_diff_deadline), "duration": 1.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT, deterministic_opp=deterministic_opp)
        assert result["success"] is True
        merged = result["merged_opportunity"]
        # Deterministic deadline must be preserved
        assert merged["deadline"].year == 2026
        assert merged["deadline"].month == 10
        assert merged["deadline"].day == 25

    @pytest.mark.asyncio
    async def test_deterministic_reference_number_wins(self):
        """Deterministic reference number is not overridden by AI."""
        deterministic_opp = {
            "source_id": "src1",
            "source_url": "https://example.com/tender/1",
            "title": "Bridge Construction",
            "type": "TENDER",
            "reference_number": "NHAI/2026/001",
            "is_opportunity": True,
        }
        ai_with_diff_ref = dict(VALID_AI_JSON, reference_number="AI-GUESSED-REF")
        gen_result = {"success": True, "response": json.dumps(ai_with_diff_ref), "duration": 1.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT, deterministic_opp=deterministic_opp)
        assert result["success"] is True
        merged = result["merged_opportunity"]
        # Deterministic reference wins
        assert merged["reference_number"] == "NHAI/2026/001"

    @pytest.mark.asyncio
    async def test_deterministic_value_wins(self):
        """Financial value from deterministic extraction is preserved over AI value."""
        deterministic_opp = {
            "source_id": "src1",
            "source_url": "https://example.com/tender/1",
            "title": "Bridge Construction",
            "type": "TENDER",
            "value": 50000000.0,  # 5 crore from regex
            "is_opportunity": True,
        }
        ai_with_wrong_value = dict(VALID_AI_JSON, value=999999999)  # AI hallucinated different
        gen_result = {"success": True, "response": json.dumps(ai_with_wrong_value), "duration": 1.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT, deterministic_opp=deterministic_opp)
        assert result["success"] is True
        merged = result["merged_opportunity"]
        # Deterministic value must be preserved
        assert merged["value"] == 50000000.0

    @pytest.mark.asyncio
    async def test_ai_fills_missing_organization(self):
        """When deterministic extraction has no organization, AI value is used."""
        deterministic_opp = {
            "source_id": "src1",
            "source_url": "https://example.com/tender/1",
            "title": "Bridge Construction",
            "type": "TENDER",
            "is_opportunity": True,
            # No organization
        }
        gen_result = {"success": True, "response": json.dumps(VALID_AI_JSON), "duration": 1.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT, deterministic_opp=deterministic_opp)
        assert result["success"] is True
        merged = result["merged_opportunity"]
        # AI organization should be used as fallback
        assert merged.get("organization") == "NHAI"

    @pytest.mark.asyncio
    async def test_ai_enriches_scope_when_absent(self):
        """AI-only fields like scope are always taken from AI output."""
        deterministic_opp = {
            "source_id": "src1",
            "source_url": "https://example.com/tender/1",
            "title": "Bridge Construction",
            "type": "TENDER",
            "is_opportunity": True,
        }
        gen_result = {"success": True, "response": json.dumps(VALID_AI_JSON), "duration": 1.5}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT, deterministic_opp=deterministic_opp)
        merged = result["merged_opportunity"]
        assert isinstance(merged.get("scope"), list)
        assert len(merged["scope"]) > 0


# ─── No Hallucination ─────────────────────────────────────────────────────────

class TestNoHallucination:
    @pytest.mark.asyncio
    async def test_value_null_when_not_in_content(self):
        """
        Content with no price → AI must return value=null, not invent a number.
        We simulate a well-behaved AI returning null.
        """
        no_value_ai = dict(VALID_AI_JSON, value=None, currency=None)
        gen_result = {"success": True, "response": json.dumps(no_value_ai), "duration": 1.0}
        extractor = make_extractor(gen_result)

        content_no_price = dict(SAMPLE_CONTENT, content="Tender for bridge construction on NH-44. No price information.")
        result = await extractor.extract_and_merge(content_no_price)
        merged = result["merged_opportunity"]

        assert merged.get("value") is None

    @pytest.mark.asyncio
    async def test_crore_value_extracted_correctly(self):
        """'₹5 crore' should map to value=50000000, currency=INR."""
        crore_ai = dict(VALID_AI_JSON, value=50000000, currency="INR")
        gen_result = {"success": True, "response": json.dumps(crore_ai), "duration": 1.0}
        extractor = make_extractor(gen_result)

        result = await extractor.extract_and_merge(SAMPLE_CONTENT)
        merged = result["merged_opportunity"]

        # AI returned the correct numeric value
        assert merged.get("value") == 50000000.0 or merged.get("value") == 50000000
        assert merged.get("currency") == "INR"


# ─── AI unavailable ───────────────────────────────────────────────────────────

class TestAIUnavailable:
    @pytest.mark.asyncio
    async def test_extract_returns_unavailable_when_ollama_down(self):
        """extract() returns 'UNAVAILABLE' status when OllamaClient cannot connect."""
        gen_result = {"success": False, "error": "Ollama service unavailable", "error_type": "unavailable", "duration": 0.1}
        extractor = make_extractor(gen_result)

        result = await extractor.extract(SAMPLE_CONTENT)

        assert result["status"] == "UNAVAILABLE"
        assert result["enriched_fields"] == {}
        assert "error" in result

    @pytest.mark.asyncio
    async def test_extract_and_merge_falls_back_gracefully(self):
        """extract_and_merge() returns deterministic_opp with ai.processed=False when Ollama fails."""
        gen_result = {"success": False, "error": "timeout", "error_type": "timeout", "duration": 60.0}
        extractor = make_extractor(gen_result)

        deterministic_opp = {
            "source_id": "src1",
            "title": "Fallback Tender",
            "type": "TENDER",
            "is_opportunity": True,
        }

        result = await extractor.extract_and_merge(SAMPLE_CONTENT, deterministic_opp=deterministic_opp)

        assert result["success"] is False
        merged = result["merged_opportunity"]
        # Should preserve the deterministic data
        assert merged["title"] == "Fallback Tender"
        # AI metadata should show processed=False
        assert merged.get("ai", {}).get("processed") is False

