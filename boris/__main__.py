"""Entry point: python -m boris."""

import asyncio
import sys
from pathlib import Path

from loguru import logger

from boris.config import load_config
from boris.core.loop import main_loop

# Log to a fixed location next to the project root
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | {message}",
)
logger.add(
    _LOG_DIR / "boris.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
)


def main():
    config = load_config()
    logger.info(f"Boris v0.1.0 — {config.assistant.name}")
    logger.info(f"LLM: {config.llm.model}, STT: {config.stt.model}, TTS: {config.tts.model}")

    try:
        asyncio.run(main_loop(config))
    except KeyboardInterrupt:
        logger.info("Adiós.")


if __name__ == "__main__":
    main()
