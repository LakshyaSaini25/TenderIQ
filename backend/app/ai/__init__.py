from app.ai.ollama_client import OllamaClient
from app.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT_EXTRACTION, USER_PROMPT_TEMPLATE
from app.ai.opportunity_extractor import OpportunityAIExtractor, AIExtractionOutput

__all__ = [
    "OllamaClient",
    "OpportunityAIExtractor",
    "AIExtractionOutput",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT_EXTRACTION",
    "USER_PROMPT_TEMPLATE"
]

