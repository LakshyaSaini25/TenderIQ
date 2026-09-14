import httpx
import logging
import time
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT

    async def check_health(self) -> Dict[str, Any]:
        """
        Checks connectivity to Ollama server and lists available models.
        Returns standardized health dictionary.
        """
        endpoint = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(endpoint)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "status": "ok",
                        "provider": "ollama",
                        "model": self.default_model,
                        "available_models": models
                    }
                else:
                    return {
                        "status": "unavailable",
                        "provider": "ollama",
                        "error": f"Ollama returned HTTP {response.status_code}"
                    }
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RequestError) as e:
            logger.debug(f"Ollama health check failed: {e}")
            return {
                "status": "unavailable",
                "provider": "ollama",
                "error": "Cannot connect to Ollama service"
            }
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama health: {e}")
            return {
                "status": "unavailable",
                "provider": "ollama",
                "error": str(e)
            }

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        format: Optional[str] = "json"
    ) -> Dict[str, Any]:
        """
        Sends generation prompt to Ollama /api/generate endpoint with structured format.
        """
        target_model = model or self.default_model
        endpoint = f"{self.base_url}/api/generate"

        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic factual extraction
            }
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                response = await client.post(endpoint, json=payload)
                duration = time.time() - start_time

                if response.status_code == 200:
                    data = response.json()
                    raw_response = data.get("response", "")
                    return {
                        "success": True,
                        "response": raw_response,
                        "model": target_model,
                        "duration": duration,
                        "eval_count": data.get("eval_count"),
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "error": f"Model '{target_model}' not found on Ollama. Pull it with: ollama pull {target_model}",
                        "error_type": "model_not_found",
                        "duration": duration
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ollama responded with HTTP {response.status_code}: {response.text}",
                        "error_type": "http_error",
                        "duration": duration
                    }

        except httpx.TimeoutException:
            duration = time.time() - start_time
            logger.warning(f"Ollama generation timed out after {self.timeout} seconds.")
            return {
                "success": False,
                "error": f"Ollama request timed out after {self.timeout}s",
                "error_type": "timeout",
                "duration": duration
            }
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            duration = time.time() - start_time
            logger.warning(f"Failed to connect to Ollama at {self.base_url}: {e}")
            return {
                "success": False,
                "error": "Ollama service unavailable or connection refused",
                "error_type": "unavailable",
                "duration": duration
            }
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error during Ollama inference: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "internal_error",
                "duration": duration
            }

