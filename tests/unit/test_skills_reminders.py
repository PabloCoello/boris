"""Tests for boris.skills.reminders module."""

import asyncio
from datetime import datetime, timedelta

import pytest

from boris.skills.reminders import (
    ReminderSkill,
    RemindersListSkill,
    ReminderStore,
    watch_reminders,
)


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


# ── Persistence ───────────────────────────────────────────────────────


def test_store_persists_and_reloads(tmp_path):
    path = tmp_path / "reminders.json"
    store = ReminderStore(path)
    store.add("Regar las plantas", datetime(2026, 7, 1, 10, 0))

    reloaded = ReminderStore(path)
    assert len(reloaded.all()) == 1
    assert reloaded.all()[0].text == "Regar las plantas"
    assert reloaded.all()[0].dt == datetime(2026, 7, 1, 10, 0)


def test_store_remove_persists(tmp_path):
    path = tmp_path / "reminders.json"
    store = ReminderStore(path)
    store.add("Uno", datetime(2026, 7, 1, 10, 0))
    store.add("Dos", datetime(2026, 7, 2, 10, 0))
    store.remove(store.all()[0])

    reloaded = ReminderStore(path)
    assert [r.text for r in reloaded.all()] == ["Dos"]


def test_store_ignores_corrupt_file(tmp_path):
    path = tmp_path / "reminders.json"
    path.write_text("{esto no es json", encoding="utf-8")
    store = ReminderStore(path)
    assert store.all() == []


def test_store_without_path_is_in_memory(tmp_path):
    store = ReminderStore()
    store.add("Efímero", datetime(2026, 7, 1, 10, 0))
    assert len(store.all()) == 1
    assert list(tmp_path.iterdir()) == []


# ── Due / watcher ─────────────────────────────────────────────────────


def test_due_returns_only_past_reminders():
    store = ReminderStore()
    past = datetime.now() - timedelta(minutes=5)
    future = datetime.now() + timedelta(hours=1)
    store.add("Pasado", past)
    store.add("Futuro", future)

    due = store.due()
    assert [r.text for r in due] == ["Pasado"]
    assert [r.text for r in store.pending()] == ["Futuro"]


@pytest.mark.asyncio
async def test_watcher_announces_and_removes_due():
    store = ReminderStore()
    store.add("Sacar la basura", datetime.now() - timedelta(seconds=1))
    announced = []

    async def announce(reminder):
        announced.append(reminder.text)

    task = asyncio.create_task(watch_reminders(store, announce, interval_s=0.01))
    await asyncio.sleep(0.05)
    task.cancel()

    assert announced == ["Sacar la basura"]
    assert store.all() == []


@pytest.mark.asyncio
async def test_watcher_keeps_reminder_if_announce_fails():
    store = ReminderStore()
    store.add("Importante", datetime.now() - timedelta(seconds=1))

    async def announce(reminder):
        raise RuntimeError("TTS roto")

    task = asyncio.create_task(watch_reminders(store, announce, interval_s=0.01))
    await asyncio.sleep(0.05)
    task.cancel()

    assert [r.text for r in store.all()] == ["Importante"]
