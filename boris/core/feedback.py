"""Feedback sounds (beeps and chimes) for interaction events."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

if TYPE_CHECKING:
    from boris.vad.silero import AudioListener

SAMPLE_RATE = 48000


def _tone(freq: float, duration_s: float, volume: float = 1.0) -> np.ndarray:
    """Generate a sine tone with smooth fade in/out."""
    n = int(SAMPLE_RATE * duration_s)
    t = np.linspace(0, duration_s, n, dtype=np.float32)
    wave = np.sin(2 * np.pi * freq * t) * volume
    # Fade in/out (10ms each)
    fade = int(SAMPLE_RATE * 0.01)
    if fade > 0 and n > 2 * fade:
        wave[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
        wave[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    return wave


def _silence(duration_s: float) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * duration_s), dtype=np.float32)


class FeedbackPlayer:
    """Play short feedback sounds. All methods are blocking."""

    def __init__(self, enabled: bool = True, volume: float = 0.7):
        self._enabled = enabled
        self._volume = max(0.0, min(1.0, volume))
        self._listener: AudioListener | None = None

    def set_listener(self, listener: AudioListener):
        self._listener = listener

    def _play(self, audio: np.ndarray):
        if not self._enabled:
            return
        audio = audio * self._volume
        if self._listener:
            self._listener.mute()
        try:
            sd.play(audio, samplerate=SAMPLE_RATE)
            sd.wait()
        finally:
            if self._listener:
                self._listener.unmute()

    def play_detect(self):
        """Short ascending beep — wake word detected (command mode)."""
        audio = np.concatenate([
            _tone(600, 0.05),
            _tone(900, 0.05),
        ])
        self._play(audio)

    def play_summon(self):
        """Grave chime — entering summoned mode."""
        audio = np.concatenate([
            _tone(220, 0.12),
            _silence(0.03),
            _tone(330, 0.12),
            _silence(0.03),
            _tone(440, 0.15),
        ])
        self._play(audio)

    def play_confirm(self):
        """Confirmation beep — skill executed OK."""
        self._play(_tone(800, 0.08))

    def play_error(self):
        """Double descending beep — something failed."""
        audio = np.concatenate([
            _tone(600, 0.08),
            _silence(0.04),
            _tone(400, 0.10),
        ])
        self._play(audio)

    def play_dismiss(self):
        """Descending chime — exiting summoned mode."""
        audio = np.concatenate([
            _tone(440, 0.12),
            _silence(0.03),
            _tone(330, 0.12),
            _silence(0.03),
            _tone(220, 0.15),
        ])
        self._play(audio)
