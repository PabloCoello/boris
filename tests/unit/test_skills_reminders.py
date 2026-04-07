"""Tests for boris.skills.reminders module."""

import pytest

from boris.skills.reminders import ReminderSkill, RemindersListSkill, ReminderStore


@pytest.fixture(autouse=True)
def fresh_store():
    """Give each test a fresh store to avoid state leakage."""
    import boris.skills.reminders as mod
    mod._store = ReminderStore()
    yield mod._store


@pytest.mark.asyncio
async def test_create_reminder():
    skill = ReminderSkill()
    result = await skill.run(
        text="Llamar al médico",
        datetime="2026-04-07T10:00:00",
        timeout=5.0,
    )
    assert result.ok is True
    assert "Llamar al médico" in result.message


@pytest.mark.asyncio
async def test_create_reminder_missing_text():
    skill = ReminderSkill()
    result = await skill.run(timeout=5.0)
    assert result.ok is False


@pytest.mark.asyncio
async def test_list_reminders_empty():
    skill = RemindersListSkill()
    result = await skill.run(timeout=5.0)
    assert result.ok is True
    assert "no hay" in result.message.lower() or "ningún" in result.message.lower()


@pytest.mark.asyncio
async def test_list_reminders_after_create():
    reminder_skill = ReminderSkill()
    list_skill = RemindersListSkill()

    # They share the same store
    store = reminder_skill._store
    list_skill._store = store

    await reminder_skill.run(text="Comprar leche", datetime="2026-04-07T09:00:00", timeout=5.0)

    result = await list_skill.run(timeout=5.0)
    assert result.ok is True
    assert "Comprar leche" in result.message
