"""Voice Activity Detection with silero-vad."""

from __future__ import annotations

import asyncio
import queue
import time
from collections import deque

import numpy as np
import sounddevice as sd
import torch
from loguru import logger

from boris.config import AssistantConfig, AudioConfig

# Audio params
SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512  # silero-vad requires exactly 512 samples at 16kHz (32ms)
SILENCE_TIMEOUT_S = 1.5  # seconds of silence to end utterance
PRE_SPEECH_CHUNKS = 15  # keep ~480ms before speech starts (captures first word)
SPEECH_ONSET_CHUNKS = 4  # ~128ms of consecutive speech to trigger


class AudioListener:
    """Listens for speech, records until silence."""

    def __init__(self, config: AssistantConfig, audio_config: AudioConfig):
        self.config = config
        self.audio_config = audio_config
        self._muted = False
        self._input_channels = 1

        # Load silero VAD
        self.vad_model, _ = torch.hub.load(
            "snakers4/silero-vad", "silero_vad", trust_repo=True
        )
        self.vad_model.eval()

        # Resolve device name to ID
        self._resolved_device = self._resolve_device(audio_config.input_device_name)
        dev_label = (
            f"{audio_config.input_device_name} (id={self._resolved_device})"
            if self._resolved_device is not None
            else "default"
        )
        logger.info(f"AudioListener ready: mic={dev_label}")

    @property
    def muted(self) -> bool:
        return self._muted

    def mute(self):
        self._muted = True
        logger.debug("Micrófono silenciado (echo cancel)")

    def unmute(self):
        self._muted = False
        logger.debug("Micrófono reactivado")

    def _check_vad(self, audio_chunk: np.ndarray) -> float:
        """Return speech probability for a 512-sample chunk."""
        tensor = torch.from_numpy(audio_chunk).float()
        return self.vad_model(tensor, SAMPLE_RATE).item()

    @staticmethod
    def _resolve_device(name: str | None) -> int | None:
        """Find device ID by name substring. Returns None for system default."""
        if not name:
            return None
        for i, d in enumerate(sd.query_devices()):
            if name.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i
        logger.warning(f"Micrófono '{name}' no encontrado, usando default")
        return None

    def _make_input_stream(self, blocksize: int, callback) -> sd.InputStream:
        """Create an InputStream with the configured device."""
        dev = self._resolved_device
        channels = 1
        if dev is not None:
            info = sd.query_devices(dev)
            channels = info["max_input_channels"]
        self._input_channels = channels

        return sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=channels,
            dtype="float32",
            blocksize=blocksize,
            callback=callback,
            device=dev,
        )

    def _to_mono(self, indata: np.ndarray) -> np.ndarray:
        """Convert multi-channel input to mono."""
        if self._input_channels == 1:
            return indata[:, 0].copy()
        return indata.mean(axis=1).copy()

    async def listen(self) -> np.ndarray:
        """Wait for speech, record until silence, return audio.

        Audio callback only enqueues raw chunks — VAD inference runs in a
        separate consumer thread to avoid blocking the sounddevice C callback.
        """
        logger.info("Esperando que hables...")
        t_start = time.perf_counter()
        loop = asyncio.get_event_loop()

        # Thread-safe queue: callback produces, consumer thread processes
        audio_q: queue.Queue[np.ndarray | None] = queue.Queue()

        # Results shared with consumer thread
        audio_buffer: list[np.ndarray] = []
        done = asyncio.Event()

        def audio_callback(indata: np.ndarray, frames: int, time_info, status):
            if self._muted:
                return
            audio_q.put(self._to_mono(indata))

        def vad_consumer():
            """Process audio chunks from the queue — runs in a thread."""
            pre_buffer: deque[np.ndarray] = deque(maxlen=PRE_SPEECH_CHUNKS)
            mono_acc = np.array([], dtype=np.float32)
            consecutive_speech = 0
            speech_started = False
            silence_start = None

            while True:
                try:
                    chunk = audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue

                if chunk is None:  # sentinel — stream closed
                    break

                mono_acc = np.concatenate([mono_acc, chunk])

                while len(mono_acc) >= CHUNK_SAMPLES:
                    vad_chunk = mono_acc[:CHUNK_SAMPLES]
                    mono_acc = mono_acc[CHUNK_SAMPLES:]

                    prob = self._check_vad(vad_chunk)

                    if not speech_started:
                        pre_buffer.append(vad_chunk)
                        if prob > 0.5:
                            consecutive_speech += 1
                            if consecutive_speech >= SPEECH_ONSET_CHUNKS:
                                speech_started = True
                                audio_buffer.extend(list(pre_buffer))
                                logger.debug("Voz detectada, grabando...")
                        else:
                            consecutive_speech = 0
                    else:
                        audio_buffer.append(vad_chunk)
                        if prob < 0.3:
                            if silence_start is None:
                                silence_start = time.perf_counter()
                            elif time.perf_counter() - silence_start > SILENCE_TIMEOUT_S:
                                loop.call_soon_threadsafe(done.set)
                                return
                        else:
                            silence_start = None

        stream = self._make_input_stream(CHUNK_SAMPLES, audio_callback)

        with stream:
            consumer_task = loop.run_in_executor(None, vad_consumer)
            try:
                await asyncio.wait_for(done.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                if not audio_buffer:
                    logger.debug("Timeout sin detectar voz")
                else:
                    logger.warning("Utterance recording timeout (30s)")

        # Signal the consumer to exit and wait for it
        audio_q.put(None)
        await consumer_task

        if audio_buffer:
            audio = np.concatenate(audio_buffer)
        else:
            audio = np.zeros(SAMPLE_RATE, dtype=np.float32)

        duration_s = len(audio) / SAMPLE_RATE
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.debug(f"Utterance: {duration_s:.1f}s de audio en {elapsed_ms:.0f}ms")

        return audio
