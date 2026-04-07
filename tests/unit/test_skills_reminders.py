"""Tests for boris.skills.reminders module."""

import pytest

from boris.skills.reminders import ReminderSkill, RemindersListSkill, ReminderStore


@pytest.fixture
def store():
    return ReminderStore()


@pytest.mark.asyncio
async def test_create_reminder(store):
    skill = ReminderSkill(store)
    result = await skill.run(
        text="Llamar al médico",
        datetime="2026-04-07T10:00:00",
        timeout=5.0,
    )
    assert result.ok is True
    assert "Llamar al médico" in result.message


@pytest.mark.asyncio
async def test_create_reminder_missing_text(store):
    skill = ReminderSkill(store)
    result = await skill.run(timeout=5.0)
    assert result.ok is False


@pytest.mark.asyncio
async def test_list_reminders_empty(store):
    skill = RemindersListSkill(store)
    result = await skill.run(timeout=5.0)
    assert result.ok is True
    assert "no hay" in result.message.lower() or "ningún" in result.message.lower()


@pytest.mark.asyncio
async def test_list_reminders_after_create(store):
    reminder_skill = ReminderSkill(store)
    list_skill = RemindersListSkill(store)

    await reminder_skill.run(text="Comprar leche", datetime="2026-04-07T09:00:00", timeout=5.0)

    result = await list_skill.run(timeout=5.0)
    assert result.ok is True
    assert "Comprar leche" in result.message
