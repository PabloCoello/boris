"""Integration tests for Ollama LLM client. Requires Ollama running."""

from __future__ import annotations

import pytest

from boris.config import load_config
from boris.llm.ollama import OllamaClient


@pytest.fixture
def llm_client() -> OllamaClient:
    cfg = load_config()
    return OllamaClient(cfg.llm, cfg.secrets)


@pytest.mark.asyncio
async def test_chat_full_returns_response(llm_client: OllamaClient):
    """Test that chat_full returns a non-empty string."""
    response = await llm_client.chat_full(
        [{"role": "user", "content": "Responde solo con la palabra: Boris"}]
    )
    assert len(response) > 0
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_chat_streaming_yields_tokens(llm_client: OllamaClient):
    """Test that chat yields tokens incrementally."""
    tokens = []
    async for token in llm_client.chat(
        [{"role": "user", "content": "Cuenta del 1 al 5, solo los números."}]
    ):
        tokens.append(token)
    assert len(tokens) > 1  # Should yield multiple tokens
    full_text = "".join(tokens)
    assert len(full_text) > 0
