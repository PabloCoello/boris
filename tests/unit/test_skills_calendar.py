"""Tests for boris.skills.calendar module."""

from unittest.mock import MagicMock

import pytest

from boris.skills.calendar import CalendarSkill


@pytest.fixture
def skill(tmp_path):
    creds = tmp_path / "credentials.json"
    creds.write_text("{}")
    return CalendarSkill(str(creds))


@pytest.mark.asyncio
async def test_no_credentials_file():
    skill = CalendarSkill("/nonexistent/credentials.json")
    result = await skill.run(timeout=5.0)
    assert result.ok is False
    assert "oauth-setup.md" in result.message


@pytest.mark.asyncio
async def test_no_events(skill):
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}
    skill._service = mock_service

    result = await skill.run(days=7, timeout=5.0)
    assert result.ok is True
    assert "No hay eventos" in result.message


@pytest.mark.asyncio
async def test_returns_events(skill):
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "start": {"dateTime": "2026-04-07T10:00:00+02:00"},
                "summary": "Reunión de equipo",
            },
            {
                "start": {"date": "2026-04-08"},
                "summary": "Día festivo",
            },
        ]
    }
    skill._service = mock_service

    result = await skill.run(days=7, timeout=5.0)
    assert result.ok is True
    assert "Reunión de equipo" in result.message
    assert "Día festivo" in result.message


@pytest.mark.asyncio
async def test_default_days(skill):
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}
    skill._service = mock_service

    await skill.run(timeout=5.0)

    call_kwargs = mock_service.events.return_value.list.call_args[1]
    assert call_kwargs["maxResults"] == 20
    assert call_kwargs["singleEvents"] is True


@pytest.mark.asyncio
async def test_invalid_days_defaults_to_7(skill):
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}
    skill._service = mock_service

    result = await skill.run(days="invalid", timeout=5.0)
    assert result.ok is True


@pytest.mark.asyncio
async def test_api_error(skill):
    mock_service = MagicMock()
    mock_service.events.return_value.list.return_value.execute.side_effect = Exception("API down")
    skill._service = mock_service

    result = await skill.run(timeout=5.0)
    assert result.ok is False
    assert "Error al consultar" in result.message
