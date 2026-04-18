"""Interaction state for the Boris main loop."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto


class InteractionMode(Enum):
    IDLE = auto()
    LISTENING = auto()
    COMMAND = auto()
    SUMMONED = auto()


@dataclass
class SessionState:
    """Mutable state for one interaction session."""

    mode: InteractionMode = InteractionMode.IDLE
    history: list[dict[str, str]] = field(default_factory=list)
    last_activity: float = field(default_factory=time.monotonic)
    session_start_idx: int = 0  # history index when summoned session started

    def reset_activity(self):
        self.last_activity = time.monotonic()

    def seconds_since_activity(self) -> float:
        return time.monotonic() - self.last_activity
