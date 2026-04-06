"""Tests for boris.memory.writer module."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from boris.memory.writer import save_episodic


@pytest.fixture
def history():
    return [
        {"role": "user", "content": "Boris, ¿qué hora es?"},
        {"role": "assistant", "content": "Son las 10 de la mañana, mi señor."},
        {"role": "user", "content": "Ponme un recordatorio para las 3."},
        {"role": "assistant", "content": '{"tool": "reminder", "args": {"text": "Recordatorio", "datetime": "2026-04-06T15:00:00"}}'},
        {"role": "user", "content": "Gracias Boris."},
        {"role": "assistant", "content": "A su servicio, mi señor."},
    ]


@pytest.mark.asyncio
async def test_creates_episodic_file(tmp_path: Path, history):
    episodic_dir = tmp_path / "episodic"
    episodic_dir.mkdir()

    mock_llm = AsyncMock(return_value="Resumen: el señor preguntó la hora y pidió un recordatorio.")

    await save_episodic(history, episodic_dir, summarize_fn=mock_llm)

    files = list(episodic_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "Resumen" in content


@pytest.mark.asyncio
async def test_file_named_by_date(tmp_path: Path, history):
    episodic_dir = tmp_path / "episodic"
    episodic_dir.mkdir()

    mock_llm = AsyncMock(return_value="Resumen del día.")

    await save_episodic(history, episodic_dir, summarize_fn=mock_llm)

    files = list(episodic_dir.glob("*.md"))
    # Filename should be YYYY-MM-DD.md
    assert files[0].stem.count("-") == 2


@pytest.mark.asyncio
async def test_appends_to_existing_file(tmp_path: Path, history):
    episodic_dir = tmp_path / "episodic"
    episodic_dir.mkdir()

    mock_llm = AsyncMock(return_value="Segunda sesión del día.")

    # Create existing entry
    from datetime import date
    today = date.today().isoformat()
    existing = episodic_dir / f"{today}.md"
    existing.write_text("## Sesión 1\nPrimera sesión.\n")

    await save_episodic(history, episodic_dir, summarize_fn=mock_llm)

    content = existing.read_text()
    assert "Primera sesión" in content
    assert "Segunda sesión" in content


@pytest.mark.asyncio
async def test_skips_empty_history(tmp_path: Path):
    episodic_dir = tmp_path / "episodic"
    episodic_dir.mkdir()

    mock_llm = AsyncMock()

    await save_episodic([], episodic_dir, summarize_fn=mock_llm)

    files = list(episodic_dir.glob("*.md"))
    assert len(files) == 0
    mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_passes_conversation_to_llm(tmp_path: Path, history):
    episodic_dir = tmp_path / "episodic"
    episodic_dir.mkdir()

    mock_llm = AsyncMock(return_value="Resumen.")

    await save_episodic(history, episodic_dir, summarize_fn=mock_llm)

    # LLM was called with the conversation text
    call_args = mock_llm.call_args[0][0]
    assert "¿qué hora es?" in call_args
