from fastapi import APIRouter
from app.ai.ollama_client import OllamaClient
from app.schemas.opportunity import AIHealthResponse

router = APIRouter()

@router.get("/health", response_model=AIHealthResponse)
async def check_ai_health():
    """Check Ollama AI service availability and loaded models."""
    client = OllamaClient()
    result = await client.check_health()
    return AIHealthResponse(
        available=(result.get("status") == "ok"),
        model=result.get("model"),
        models_loaded=result.get("available_models") or [],
        error=result.get("error")
    )
