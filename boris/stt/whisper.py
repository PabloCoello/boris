"""Speech-to-text with faster-whisper."""

from __future__ import annotations

import asyncio
import time

import numpy as np
from faster_whisper import WhisperModel
from loguru import logger

from boris.config import STTConfig


class WhisperSTT:
    """Transcribe audio using faster-whisper on GPU."""

    def __init__(self, config: STTConfig):
        self.config = config
        logger.info(f"Cargando Whisper {config.model} en {config.device}...")
        t_start = time.perf_counter()

        self.model = WhisperModel(
            config.model,
            device=config.device,
            compute_type="float16" if config.device == "cuda" else "int8",
        )

        t_load = time.perf_counter() - t_start
        logger.info(f"Whisper cargado en {t_load:.1f}s")

    async def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe float32 audio array to text."""
        t_start = time.perf_counter()

        text = await asyncio.to_thread(self._transcribe_sync, audio)

        t_elapsed = (time.perf_counter() - t_start) * 1000
        logger.debug(f"STT: '{text}' ({t_elapsed:.0f}ms)")

        return text

    def _transcribe_sync(self, audio: np.ndarray) -> str:
        """Blocking transcription — runs in a thread."""
        segments, info = self.model.transcribe(
            audio,
            language=self.config.language,
            beam_size=5,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
