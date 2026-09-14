"""
Prompt definitions for Ollama Local AI extraction and classification.
Version: v1
"""

PROMPT_VERSION = "v1"

SYSTEM_PROMPT_EXTRACTION = """You are an expert procurement and tender intelligence analyzer.
Your task is to analyze the provided text and extract structured information about business opportunities, tenders, RFPs, and projects.

CRITICAL RULES:
1. Extract ONLY information explicitly present in the supplied content.
2. NEVER invent, hallucinate, or assume missing information.
3. Return null for fields when the information is unavailable or unmentioned.
4. Preserve precise tender numbers, dates, values, and terminology.
5. Extract lists for eligibility criteria, technical requirements, scope of work, required certifications, experience requirements, and equipment requirements as clear, concise bullet strings.
6. You MUST return ONLY a valid JSON object strictly adhering to the schema requested, with no extra conversational text or markdown explanation."""

USER_PROMPT_TEMPLATE = """Analyze the following document and extract structured opportunity details:

=== DOCUMENT CONTENT START ===
Title: {title}
URL: {url}

Content:
{content}
=== DOCUMENT CONTENT END ===

Return a JSON object strictly matching this schema:
{{
  "is_opportunity": true or false,
  "type": "TENDER" | "PROJECT" | "PROCUREMENT" | "NEWS" | "BUSINESS_OPPORTUNITY" | "OTHER",
  "title": "string or null",
  "reference_number": "string or null",
  "organization": "string or null",
  "department": "string or null",
  "description": "concise summary of the opportunity or null",
  "location": "string or null",
  "category": "string or null",
  "value": numeric value (e.g. 50000000) or null,
  "currency": "INR" | "USD" | etc or null,
  "published_at": "YYYY-MM-DD" or null,
  "deadline": "YYYY-MM-DD" or null,
  "eligibility": ["eligibility point 1", ...],
  "requirements": ["requirement 1", ...],
  "scope": ["scope item 1", ...],
  "certifications": ["certification 1", ...],
  "experience_requirements": ["experience requirement 1", ...],
  "equipment_requirements": ["equipment requirement 1", ...],
  "contacts": {{
    "emails": ["email1@...", ...],
    "phones": ["phone1", ...]
  }}
}}
"""

