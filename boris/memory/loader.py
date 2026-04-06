"""Load memory files into LLM context."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

# Rough estimate: 1 token ≈ 4 chars in Spanish text
CHARS_PER_TOKEN = 4


def _read_and_truncate(path: Path, max_tokens: int) -> str:
    """Read a file and truncate to approximately max_tokens."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def load_memory_context(
    data_dir: str | Path,
    profile_max_tokens: int = 800,
    index_max_tokens: int = 400,
) -> str:
    """Load profile.md, index.md, and entities.md into a single context string."""
    data_dir = Path(data_dir)
    sections: list[str] = []

    profile = _read_and_truncate(data_dir / "profile.md", profile_max_tokens)
    if profile:
        sections.append(f"### Perfil del señor\n{profile}")

    entities = _read_and_truncate(data_dir / "entities.md", index_max_tokens)
    if entities:
        sections.append(f"### Entidades conocidas\n{entities}")

    index = _read_and_truncate(data_dir / "index.md", index_max_tokens)
    if index:
        sections.append(f"### Índice de memoria\n{index}")

    if not sections:
        return ""

    ctx = "\n\n".join(sections)
    logger.debug(f"Memoria cargada: {len(ctx)} chars")
    return ctx
