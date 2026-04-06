"""Tests for boris.memory.loader module."""

from pathlib import Path

from boris.memory.loader import load_memory_context


def test_loads_profile_and_index(tmp_path: Path):
    profile = tmp_path / "profile.md"
    index = tmp_path / "index.md"
    profile.write_text("El señor es ingeniero de software.")
    index.write_text("- 2026-04-01: Primera conversación con Boris.")

    ctx = load_memory_context(tmp_path)
    assert "ingeniero de software" in ctx
    assert "Primera conversación" in ctx


def test_loads_entities(tmp_path: Path):
    entities = tmp_path / "entities.md"
    entities.write_text("- Casa: mansión encantada\n- Gato: Michi")

    ctx = load_memory_context(tmp_path)
    assert "Michi" in ctx


def test_missing_files_returns_empty(tmp_path: Path):
    ctx = load_memory_context(tmp_path)
    assert ctx == ""


def test_partial_files(tmp_path: Path):
    profile = tmp_path / "profile.md"
    profile.write_text("Solo perfil, sin índice.")

    ctx = load_memory_context(tmp_path)
    assert "Solo perfil" in ctx


def test_truncates_profile_to_max_tokens(tmp_path: Path):
    profile = tmp_path / "profile.md"
    profile.write_text("palabra " * 1000)  # ~1000 tokens

    ctx = load_memory_context(tmp_path, profile_max_tokens=50)
    # Should be truncated — much shorter than the full text
    assert len(ctx) < len("palabra " * 1000)


def test_truncates_index_to_max_tokens(tmp_path: Path):
    index = tmp_path / "index.md"
    index.write_text("entrada " * 1000)

    ctx = load_memory_context(tmp_path, index_max_tokens=50)
    assert len(ctx) < len("entrada " * 1000)
