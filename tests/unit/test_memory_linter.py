"""Tests for boris.memory.linter module."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from boris.memory.linter import lint_memory


@pytest.fixture
def memory_dir(tmp_path: Path):
    episodic = tmp_path / "episodic"
    episodic.mkdir()
    (episodic / "2026-04-01.md").write_text(
        "## Sesión 1\n- El señor preguntó por el clima.\n- Prefiere café con leche.\n"
    )
    (episodic / "2026-04-02.md").write_text(
        "## Sesión 1\n- El señor pidió un recordatorio.\n- Mencionó a su gato Michi.\n"
    )
    return tmp_path


@pytest.mark.asyncio
async def test_creates_profile(memory_dir: Path):
    mock_llm = AsyncMock(return_value="El señor es un ingeniero que prefiere café con leche.")

    await lint_memory(memory_dir, synthesize_fn=mock_llm)

    profile = memory_dir / "profile.md"
    assert profile.exists()
    assert "ingeniero" in profile.read_text()


@pytest.mark.asyncio
async def test_creates_entities(memory_dir: Path):
    mock_llm = AsyncMock(side_effect=[
        "Perfil sintetizado.",
        "- Michi: gato del señor",
        "- 2026-04-01: clima",
    ])

    await lint_memory(memory_dir, synthesize_fn=mock_llm)

    entities = memory_dir / "entities.md"
    assert entities.exists()
    assert "Michi" in entities.read_text()


@pytest.mark.asyncio
async def test_creates_index(memory_dir: Path):
    mock_llm = AsyncMock(side_effect=[
        "Perfil.",
        "Entidades.",
        "- 2026-04-01: clima\n- 2026-04-02: recordatorio",
    ])

    await lint_memory(memory_dir, synthesize_fn=mock_llm)

    index = memory_dir / "index.md"
    assert index.exists()
    assert "2026-04-01" in index.read_text()


@pytest.mark.asyncio
async def test_preserves_existing_profile(memory_dir: Path):
    existing_profile = memory_dir / "profile.md"
    existing_profile.write_text("Dato previo importante.")

    mock_llm = AsyncMock(return_value="Dato previo importante. Nuevos datos añadidos.")

    await lint_memory(memory_dir, synthesize_fn=mock_llm)

    # LLM should receive existing profile as context
    call_args = mock_llm.call_args_list[0][0][0]
    assert "Dato previo importante" in call_args


@pytest.mark.asyncio
async def test_no_episodics_skips(tmp_path: Path):
    episodic = tmp_path / "episodic"
    episodic.mkdir()

    mock_llm = AsyncMock()

    await lint_memory(tmp_path, synthesize_fn=mock_llm)

    mock_llm.assert_not_called()
