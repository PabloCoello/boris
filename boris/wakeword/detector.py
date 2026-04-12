"""Wake word detection using openwakeword.

Runs a dedicated listener thread that feeds 80ms audio frames into the
wake word model.  When the wake word is detected it sets an asyncio Event
so the main loop can react — including interrupting TTS playback.

The detector keeps listening even while TTS is playing (it has its own
audio stream that is never muted), which is what makes barge-in possible.
"""

from __future__ import annotations

import asyncio
import threading
import time

import numpy as np
import sounddevice as sd
from loguru import logger
from openwakeword.model import Model

# openwakeword requires 16 kHz, 80ms frames
SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1280  # 80ms at 16 kHz

DEFAULT_THRESHOLD = 0.5


class WakeWordDetector:
    """Continuously listens for a wake word on a background thread."""

    def __init__(
        self,
        model_path: str | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        device_name: str | None = None,
    ):
        self._threshold = threshold
        self._device_id = self._resolve_device(device_name)

        # Load model — custom .onnx or default pre-trained set
        if model_path:
            self._model = Model(
                wakeword_models=[model_path],
                inference_framework="onnx",
            )
        else:
            # Fallback: use "hey_jarvis" as placeholder until custom model is trained
            self._model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx",
            )

        self._model_names = list(self._model.models.keys())
        logger.info(
            f"WakeWordDetector ready: models={self._model_names}, "
            f"threshold={threshold}"
        )

        # Signalling
        self._loop: asyncio.AbstractEventLoop | None = None
        self._detected = asyncio.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _resolve_device(name: str | None) -> int | None:
        if not name:
            return None
        for i, d in enumerate(sd.query_devices()):
            if name.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i
        logger.warning(f"WakeWord: mic '{name}' not found, using default")
        return None

    # -- Public API -----------------------------------------------------------

    def start(self, loop: asyncio.AbstractEventLoop):
        """Start the background listener thread."""
        self._loop = loop
        self._stop.clear()
        self._detected.clear()
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="wakeword"
        )
        self._thread.start()

    def stop(self):
        """Signal the background thread to exit."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    async def wait(self):
        """Block until the wake word is detected (async)."""
        self._detected.clear()
        await self._detected.wait()

    def reset(self):
        """Clear the detected flag and model state so we can listen again."""
        self._detected.clear()
        self._model.reset()

    # -- Background thread ----------------------------------------------------

    def _listen_loop(self):
        """Continuously read audio and run wake word inference."""
        channels = 1
        dev = self._device_id
        if dev is not None:
            info = sd.query_devices(dev)
            channels = info["max_input_channels"]

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=channels,
            dtype="int16",
            blocksize=CHUNK_SAMPLES,
            device=dev,
        )

        logger.debug("WakeWord listener thread started")
        stream.start()

        try:
            while not self._stop.is_set():
                audio, overflowed = stream.read(CHUNK_SAMPLES)
                if overflowed:
                    logger.debug("WakeWord: audio overflow")

                # Mix to mono if multi-channel
                if channels > 1:
                    chunk = audio.mean(axis=1).astype(np.int16)
                else:
                    chunk = audio.flatten()

                prediction = self._model.predict(chunk)

                for name in self._model_names:
                    score = prediction.get(name, 0)
                    if score >= self._threshold:
                        logger.info(
                            f"Wake word '{name}' detected (score={score:.3f})"
                        )
                        if self._loop is not None:
                            self._loop.call_soon_threadsafe(self._detected.set)
                        # Small cooldown to avoid double-triggers
                        time.sleep(0.5)
                        self._model.reset()
                        break
        finally:
            stream.stop()
            stream.close()
            logger.debug("WakeWord listener thread stopped")
