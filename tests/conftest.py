"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_config(tmp_path: Path) -> tuple[Path, Path]:
    """Create temporary config.yaml and .env files, return (config_path, env_path)."""
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text(
        """
assistant:
  name: TestBoris
  language: es
  wake_word: test

stt:
  model: tiny
  language: es
  device: cpu

llm:
  model: test-model
  temperature: 0.5
  max_tokens: 256

memory:
  data_dir: /tmp/test_memory
"""
    )

    env_file = tmp_path / ".env"
    env_file.write_text(
        """
OLLAMA_HOST=http://localhost:11434
HA_TOKEN=test-token-123
"""
    )

    return config_yaml, env_file
