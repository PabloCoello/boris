"""Reminder skills: create and list reminders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from boris.skills.base import Skill, SkillResult


@dataclass
class Reminder:
    text: str
    dt: datetime


class ReminderStore:
    """In-memory reminder store (shared between create/list skills)."""

    def __init__(self):
        self.reminders: list[Reminder] = []

    def add(self, text: str, dt: datetime):
        self.reminders.append(Reminder(text=text, dt=dt))

    def pending(self) -> list[Reminder]:
        now = datetime.now()
        return [r for r in self.reminders if r.dt > now]

    def all(self) -> list[Reminder]:
        return list(self.reminders)


# Singleton store shared between both skills
_store = ReminderStore()


class ReminderSkill(Skill):
    name = "reminder"
    description = "Crea un recordatorio."

    def __init__(self):
        self._store = _store

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

    def __init__(self):
        self._store = _store

    async def execute(self, **kwargs) -> SkillResult:
        reminders = self._store.all()
        if not reminders:
            return SkillResult(ok=True, message="No hay ningún recordatorio pendiente.")

        lines = [
            f"- {r.text} ({r.dt.strftime('%d/%m/%Y %H:%M')})"
            for r in reminders
        ]
        return SkillResult(ok=True, message="Recordatorios:\n" + "\n".join(lines))
