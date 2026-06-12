"""Reminder skills: create, list, persist, and announce reminders."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from loguru import logger

from boris.skills.base import Skill, SkillResult

DEFAULT_REMINDERS_PATH = "data/reminders.json"
CHECK_INTERVAL_S = 15.0


@dataclass
class Reminder:
    text: str
    dt: datetime


class ReminderStore:
    """Reminder store shared between create/list skills and the watcher.

    With a path it persists to JSON on every change; without one it is
    in-memory only (used in tests).
    """

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else None
        self.reminders: list[Reminder] = []
        self._load()

    def _load(self):
        if self._path is None or not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self.reminders = [
                Reminder(text=item["text"], dt=datetime.fromisoformat(item["datetime"]))
                for item in data
            ]
            logger.debug(f"Reminders: {len(self.reminders)} cargados de {self._path}")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Reminders: fichero ilegible {self._path} ({e}), empezando vacío")

    def _save(self):
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [{"text": r.text, "datetime": r.dt.isoformat()} for r in self.reminders]
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def add(self, text: str, dt: datetime):
        self.reminders.append(Reminder(text=text, dt=dt))
        self._save()

    def remove(self, reminder: Reminder):
        self.reminders = [r for r in self.reminders if r is not reminder]
        self._save()

    def due(self, now: datetime | None = None) -> list[Reminder]:
        now = now or datetime.now()
        return [r for r in self.reminders if r.dt <= now]

    def pending(self) -> list[Reminder]:
        now = datetime.now()
        return [r for r in self.reminders if r.dt > now]

    def all(self) -> list[Reminder]:
        return list(self.reminders)


async def watch_reminders(
    store: ReminderStore,
    announce: Callable[[Reminder], Awaitable[None]],
    interval_s: float = CHECK_INTERVAL_S,
) -> None:
    """Background task: poll the store and announce due reminders.

    A reminder is only removed after announce() succeeds, so a TTS
    failure retries on the next tick instead of losing the reminder.
    """
    while True:
        await asyncio.sleep(interval_s)
        for reminder in store.due():
            try:
                await announce(reminder)
            except Exception as e:
                logger.error(f"Error anunciando recordatorio '{reminder.text}': {e}")
                continue
            store.remove(reminder)
            logger.info(f"Recordatorio anunciado: '{reminder.text}'")


class ReminderSkill(Skill):
    name = "reminder"
    description = "Crea un recordatorio."
    args_doc = "text (str), datetime (str ISO 8601)"

    def __init__(self, store: ReminderStore):
        self._store = store

    async def execute(self, **kwargs) -> SkillResult:
        text = kwargs.get("text")
        dt_str = kwargs.get("datetime")

        if not text:
            return SkillResult(ok=False, message="Falta el texto del recordatorio.")

        try:
            dt = datetime.fromisoformat(dt_str) if dt_str else datetime.now()
        except (TypeError, ValueError):
            return SkillResult(ok=False, message=f"Fecha inválida: {dt_str}")

        self._store.add(text, dt)
        logger.info(f"Recordatorio creado: '{text}' para {dt}")
        return SkillResult(
            ok=True,
            message=f"Recordatorio creado: '{text}' para {dt.strftime('%d/%m/%Y %H:%M')}.",
        )


class RemindersListSkill(Skill):
    name = "reminders_list"
    description = "Lista recordatorios pendientes."

    def __init__(self, store: ReminderStore):
        self._store = store

    async def execute(self, **kwargs) -> SkillResult:
        reminders = self._store.all()
        if not reminders:
            return SkillResult(ok=True, message="No hay ningún recordatorio pendiente.")

        lines = [
            f"- {r.text} ({r.dt.strftime('%d/%m/%Y %H:%M')})"
            for r in reminders
        ]
        return SkillResult(ok=True, message="Recordatorios:\n" + "\n".join(lines))
