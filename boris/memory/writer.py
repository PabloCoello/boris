"""Write episodic memory entries from conversation history."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import date
from pathlib import Path

from loguru import logger

SUMMARIZE_PROMPT = """Resume esta conversación en español en 3-5 bullet points.
Incluye: qué pidió el señor, qué acciones se ejecutaron, datos relevantes mencionados.
No incluyas saludos triviales. Sé conciso.

Conversación:
{conversation}"""


def _format_history(history: list[dict[str, str]]) -> str:
    """Format conversation history as readable text."""
    lines = []
    for msg in history:
        role = "Señor" if msg["role"] == "user" else "Boris"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


async def save_episodic(
    history: list[dict[str, str]],
    episodic_dir: str | Path,
    summarize_fn: Callable[[str], Coroutine[None, None, str]],
) -> None:
    """Summarize conversation and save/append to today's episodic file."""
    if not history:
        return

    episodic_dir = Path(episodic_dir)
    episodic_dir.mkdir(parents=True, exist_ok=True)

    conversation = _format_history(history)
    prompt = SUMMARIZE_PROMPT.format(conversation=conversation)

    summary = await summarize_fn(prompt)

    today = date.today().isoformat()
    filepath = episodic_dir / f"{today}.md"

    if filepath.exists():
        existing = filepath.read_text(encoding="utf-8")
        # Count existing sessions to number the new one
        session_count = existing.count("## Sesión") + 1
        new_content = f"{existing}\n## Sesión {session_count}\n{summary}\n"
    else:
        new_content = f"## Sesión 1\n{summary}\n"

    filepath.write_text(new_content, encoding="utf-8")
    logger.info(f"Episodic guardado: {filepath.name}")
