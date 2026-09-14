"""
Tests for OllamaClient: connectivity, timeout, and error handling.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.ai.ollama_client import OllamaClient


# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_client():
    return OllamaClient(
        base_url="http://localhost:11434",
        model="llama3.2:3b",
        timeout=10
    )


# ─── check_health() ──────────────────────────────────────────────────────────

class TestCheckHealth:
    @pytest.mark.asyncio
    async def test_health_ok(self):
        """Returns 'ok' when Ollama responds with model list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [{"name": "llama3.2:3b"}, {"name": "mistral:7b"}]
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.check_health()

        assert result["status"] == "ok"
        assert result["model"] == "llama3.2:3b"
        assert "llama3.2:3b" in result["available_models"]

    @pytest.mark.asyncio
    async def test_health_unavailable_on_connect_error(self):
        """Returns 'unavailable' when Ollama service is not running."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.check_health()

        assert result["status"] == "unavailable"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_unavailable_on_non_200(self):
        """Returns 'unavailable' when Ollama returns non-200."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.check_health()

        assert result["status"] == "unavailable"


# ─── generate() ──────────────────────────────────────────────────────────────

class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Returns success=True with response text on HTTP 200."""
        sample_json = json.dumps({"is_opportunity": True, "type": "TENDER", "title": "Test"})
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": sample_json, "eval_count": 42}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.generate(prompt="Analyze this tender")

        assert result["success"] is True
        assert "is_opportunity" in result["response"]
        assert result["model"] == "llama3.2:3b"

    @pytest.mark.asyncio
    async def test_generate_timeout(self):
        """Returns success=False with error_type='timeout' on TimeoutException."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.generate(prompt="Analyze this tender")

        assert result["success"] is False
        assert result["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_generate_service_unavailable(self):
        """Returns success=False with error_type='unavailable' on ConnectError."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Refused"))
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.generate(prompt="Analyze this tender")

        assert result["success"] is False
        assert result["error_type"] == "unavailable"

    @pytest.mark.asyncio
    async def test_generate_model_not_found(self):
        """Returns success=False with error_type='model_not_found' on HTTP 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "model not found"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            client = make_client()
            result = await client.generate(prompt="test")

        assert result["success"] is False
        assert result["error_type"] == "model_not_found"

