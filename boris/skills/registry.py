"""Build the skill registry from config."""

from __future__ import annotations

from loguru import logger

from boris.config import Config
from boris.skills.base import SkillRegistry
from boris.skills.reminders import ReminderSkill, RemindersListSkill, ReminderStore


def build_registry(config: Config, reminder_store: ReminderStore | None = None) -> SkillRegistry:
    """Create and populate the skill registry based on config.

    Pass a reminder_store to share it with the reminder watcher; by
    default an in-memory store is created.
    """
    registry = SkillRegistry()

    if reminder_store is None:
        reminder_store = ReminderStore()
    registry.register(ReminderSkill(reminder_store))
    registry.register(RemindersListSkill(reminder_store))

    if config.skills.search.url:
        from boris.skills.search import SearchSkill

        registry.register(SearchSkill(config.skills.search.url))

    if config.secrets.spotify_client_id:
        from boris.skills.music import MusicControlSkill, MusicPlaySkill

        registry.register(MusicPlaySkill(
            client_id=config.secrets.spotify_client_id,
            client_secret=config.secrets.spotify_client_secret,
        ))
        registry.register(MusicControlSkill(
            client_id=config.secrets.spotify_client_id,
            client_secret=config.secrets.spotify_client_secret,
        ))

    if config.secrets.google_credentials_json:
        from boris.skills.calendar import CalendarSkill

        registry.register(CalendarSkill(
            credentials_json=config.secrets.google_credentials_json,
        ))

    if config.skills.garmin.enabled and config.secrets.garmin_email:
        from boris.skills.garmin import GarminSkill

        registry.register(GarminSkill(
            email=config.secrets.garmin_email,
            password=config.secrets.garmin_password,
        ))

    logger.info(f"Skills registradas: {registry.list_names()}")
    return registry
