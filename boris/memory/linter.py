"""Memory linter: synthesize profile, entities, and index from episodics.

Run manually: uv run python -m boris.memory.linter
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from pathlib import Path

from loguru import logger

LINT_PROMPT = """Analiza estas notas episódicas y genera TRES secciones separadas por la línea "---".

SECCIÓN 1 — PERFIL: Sintetiza un perfil del usuario. Incluye preferencias, rutinas, personas/mascotas, datos relevantes.
Mantén lo que ya se sabía del perfil anterior y añade lo nuevo. Máximo 800 tokens.

SECCIÓN 2 — ENTIDADES: Lista todas las entidades mencionadas (personas, mascotas, lugares, dispositivos).
Formato: una línea por entidad con "- Nombre: descripción breve".

SECCIÓN 3 — ÍNDICE: Genera un índice breve. Formato: una línea por día con "- YYYY-MM-DD: resumen de 5-10 palabras".
Máximo 400 tokens.

Todo en español.

Perfil anterior:
{existing_profile}

Notas episódicas:
{episodics}"""


def _read_episodics(episodic_dir: Path) -> str:
    """Read all episodic files, sorted by date."""
    files = sorted(episodic_dir.glob("*.md"))
    if not files:
        return ""
    parts = []
    for f in files:
        parts.append(f"--- {f.stem} ---\n{f.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(parts)


async def lint_memory(
    data_dir: str | Path,
    synthesize_fn: Callable[[str], Coroutine[None, None, str]],
) -> None:
    """Synthesize profile.md, entities.md, and index.md from episodic entries."""
    data_dir = Path(data_dir)
    episodic_dir = data_dir / "episodic"

    episodics_text = _read_episodics(episodic_dir)
    if not episodics_text:
        logger.info("No hay episódicos, nada que sintetizar.")
        return

    existing_profile = ""
    profile_path = data_dir / "profile.md"
    if profile_path.exists():
        existing_profile = profile_path.read_text(encoding="utf-8").strip()

    # Single LLM call for all three outputs
    result = await synthesize_fn(
        LINT_PROMPT.format(existing_profile=existing_profile or "(vacío)", episodics=episodics_text)
    )

    # Split into sections by "---" separator
    sections = [s.strip() for s in result.split("---")]

    profile = sections[0] if len(sections) > 0 else ""
    entities = sections[1] if len(sections) > 1 else ""
    index = sections[2] if len(sections) > 2 else ""

    profile_path.write_text(profile + "\n", encoding="utf-8")
    logger.info("profile.md actualizado")

    (data_dir / "entities.md").write_text(entities + "\n", encoding="utf-8")
    logger.info("entities.md actualizado")

    (data_dir / "index.md").write_text(index + "\n", encoding="utf-8")
    logger.info("index.md actualizado")


async def _main():
    """CLI entry point: synthesize memory from episodics using Ollama."""
    import sys

    from boris.config import load_config
    from boris.llm.ollama import OllamaClient

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    config = load_config()
    llm = OllamaClient(config.llm, config.secrets)

    logger.info(f"Linting memoria en {config.memory.data_dir}...")
    await lint_memory(config.memory.data_dir, synthesize_fn=llm.prompt)
    logger.info("Linting completo.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
