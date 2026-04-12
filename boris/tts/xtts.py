"""Text-to-speech with Coqui TTS and echo cancellation."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd
from loguru import logger
from scipy.signal import resample

from boris.config import TTSConfig
from boris.tts.normalize import normalize_for_tts

if TYPE_CHECKING:
    from boris.vad.silero import AudioListener

# Model configs: name → (coqui model id, sample rate, needs speaker_wav)
TTS_MODELS = {
    "vits_es": ("tts_models/es/css10/vits", 22050, False),
    "xtts_v2": ("tts_models/multilingual/multi-dataset/xtts_v2", 22050, True),
}


class TTSEngine:
    """Synthesize speech with Coqui TTS and play through speakers."""

    def __init__(self, config: TTSConfig):
        self.config = config
        self._listener: AudioListener | None = None

        model_key = config.model
        if model_key not in TTS_MODELS:
            model_key = "vits_es"
            logger.warning(f"Modelo TTS '{config.model}' no reconocido, usando vits_es")

        model_id, self._sample_rate, self._needs_speaker = TTS_MODELS[model_key]

        logger.info(f"Cargando TTS modelo {model_key} ({model_id})...")
        t_start = time.perf_counter()

        from TTS.api import TTS

        self.tts = TTS(model_id).to("cpu")

        # Resolve speaker reference WAV (only for XTTS)
        self._speaker_wav = None
        if self._needs_speaker and config.speaker_wav and Path(config.speaker_wav).exists():
            self._speaker_wav = config.speaker_wav

        t_load = time.perf_counter() - t_start
        logger.info(f"TTS cargado en {t_load:.1f}s")

    def set_listener(self, listener: AudioListener):
        """Register the audio listener for echo cancellation."""
        self._listener = listener

    def stop(self):
        """Interrupt playback immediately (called from any thread)."""
        sd.stop()
        # Unmute mic right away so the listener can capture speech
        if self._listener:
            self._listener.unmute()

    async def speak(self, text: str):
        """Synthesize and play text. Mutes microphone during playback."""
        if not text.strip():
            return

        t_start = time.perf_counter()

        # Echo cancel: mute mic before speaking
        if self._listener:
            self._listener.mute()

        try:
            audio, t_synth = await asyncio.to_thread(self._synthesize, text)

            # Play audio via default device at 48kHz
            await asyncio.to_thread(self._play, audio)

            t_total = (time.perf_counter() - t_start) * 1000
            logger.debug(
                f"TTS: synth={t_synth:.0f}ms, total={t_total:.0f}ms, "
                f"text='{text[:50]}...'"
            )

        finally:
            # Echo cancel: unmute mic after speaking
            if self._listener:
                self._listener.unmute()

    def _synthesize(self, text: str) -> tuple[np.ndarray, float]:
        """Blocking synthesis — runs in a thread. Returns (audio_48k, synth_ms)."""
        t_synth_start = time.perf_counter()

        text = normalize_for_tts(text)
        tts_kwargs: dict = {"text": text}
        if self._needs_speaker:
            tts_kwargs["language"] = self.config.language
            if self._speaker_wav:
                tts_kwargs["speaker_wav"] = self._speaker_wav
            else:
                tts_kwargs["speaker"] = "Ana Florence"

        wav = self.tts.tts(**tts_kwargs)
        audio = np.array(wav, dtype=np.float32)

        # Resample to 48kHz for pipewire/ALSA compatibility
        if self._sample_rate != 48000:
            n_samples = int(len(audio) * 48000 / self._sample_rate)
            audio = resample(audio, n_samples).astype(np.float32)

        t_synth = (time.perf_counter() - t_synth_start) * 1000
        return audio, t_synth

    @staticmethod
    def _play(audio: np.ndarray):
        """Blocking playback — runs in a thread."""
        sd.play(audio, samplerate=48000)
        sd.wait()
