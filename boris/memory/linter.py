"""Memory linter: synthesize profile, entities, and index from episodics.

Run manually: uv run python -m boris.memory.linter
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from pathlib import Path

from loguru import logger

PROFILE_PROMPT = """Sintetiza un perfil del usuario a partir de estas notas episódicas.
Incluye: preferencias, rutinas, personas y mascotas mencionadas, datos relevantes.
Mantén lo que ya se sabía del perfil anterior y añade lo nuevo.
Máximo 800 tokens. En español.

Perfil anterior:
{existing_profile}

Notas episódicas:
{episodics}"""

ENTITIES_PROMPT = """Extrae todas las entidades mencionadas (personas, mascotas, lugares, dispositivos) \
de estas notas episódicas. Formato: una línea por entidad con "- Nombre: descripción breve".
En español.

Notas episódicas:
{episodics}"""

INDEX_PROMPT = """Genera un índice breve de estas notas episódicas.
Formato: una línea por día con "- YYYY-MM-DD: resumen de 5-10 palabras".
Máximo 400 tokens. En español.

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

    # Profile
    existing_profile = ""
    profile_path = data_dir / "profile.md"
    if profile_path.exists():
        existing_profile = profile_path.read_text(encoding="utf-8").strip()

    profile = await synthesize_fn(
        PROFILE_PROMPT.format(existing_profile=existing_profile or "(vacío)", episodics=episodics_text)
    )
    profile_path.write_text(profile + "\n", encoding="utf-8")
    logger.info("profile.md actualizado")

    # Entities
    entities = await synthesize_fn(
        ENTITIES_PROMPT.format(episodics=episodics_text)
    )
    (data_dir / "entities.md").write_text(entities + "\n", encoding="utf-8")
    logger.info("entities.md actualizado")

    # Index
    index = await synthesize_fn(
        INDEX_PROMPT.format(episodics=episodics_text)
    )
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
