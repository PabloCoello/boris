"""Async Ollama client with streaming and latency measurement."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

import ollama as ollama_lib
from loguru import logger

from boris.config import LLMConfig, SecretsConfig


class OllamaClient:
    """Wrapper around ollama-python with async streaming."""

    def __init__(self, config: LLMConfig, secrets: SecretsConfig):
        self.config = config
        self.client = ollama_lib.AsyncClient(host=secrets.ollama_host)

    async def chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """Stream chat completion, yielding tokens. Logs latency metrics."""
        t_start = time.perf_counter()
        first_token_logged = False

        stream = await self.client.chat(
            model=self.config.model,
            messages=messages,
            stream=True,
            options={
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        )

        async for chunk in stream:
            token = chunk.message.content
            if token:
                if not first_token_logged:
                    t_first = time.perf_counter()
                    logger.debug(f"LLM first token: {(t_first - t_start) * 1000:.0f}ms")
                    first_token_logged = True
                yield token

        t_end = time.perf_counter()
        logger.debug(f"LLM total: {(t_end - t_start) * 1000:.0f}ms")

    async def chat_full(self, messages: list[dict[str, str]]) -> str:
        """Non-streaming chat, returns full response."""
        tokens = []
        async for token in self.chat(messages):
            tokens.append(token)
        return "".join(tokens)

    async def prompt(self, text: str) -> str:
        """Single-prompt convenience: wraps text as a user message."""
        return await self.chat_full([{"role": "user", "content": text}])
