"""Build the skill registry from config."""

from __future__ import annotations

from loguru import logger

from boris.config import Config
from boris.skills.base import SkillRegistry


def build_registry(config: Config) -> SkillRegistry:
    """Create and populate the skill registry based on config."""
    registry = SkillRegistry()

    # Import and register skills conditionally
    from boris.skills.reminders import ReminderSkill, RemindersListSkill

    registry.register(ReminderSkill())
    registry.register(RemindersListSkill())

    if config.skills.search.url:
        from boris.skills.search import SearchSkill

        registry.register(SearchSkill(config.skills.search.url))

    if config.skills.garmin.enabled and config.secrets.garmin_email:
        from boris.skills.garmin import GarminSkill

        registry.register(GarminSkill(
            email=config.secrets.garmin_email,
            password=config.secrets.garmin_password,
        ))

    logger.info(f"Skills registradas: {registry.list_names()}")
    return registry
