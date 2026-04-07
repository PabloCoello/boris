"""Tests for boris.skills.garmin module."""

from unittest.mock import MagicMock, patch

import pytest

from boris.skills.garmin import GarminSkill


@pytest.fixture
def skill():
    return GarminSkill(email="test@test.com", password="pass123")


@pytest.mark.asyncio
async def test_sleep_metric(skill):
    mock_client = MagicMock()
    mock_client.get_sleep_data.return_value = {
        "dailySleepDTO": {
            "sleepTimeSeconds": 24180,
            "deepSleepSeconds": 7200,
            "lightSleepSeconds": 10800,
            "remSleepSeconds": 5400,
            "awakeSleepSeconds": 780,
        }
    }

    with patch.object(skill, "_get_client", return_value=mock_client):
        result = await skill.run(metric="sleep", timeout=5.0)

    assert result.ok is True
    assert "6h" in result.message or "6 h" in result.message


@pytest.mark.asyncio
async def test_steps_metric(skill):
    mock_client = MagicMock()
    mock_client.get_stats.return_value = {
        "totalSteps": 8542,
        "totalDistanceMeters": 6230.5,
    }

    with patch.object(skill, "_get_client", return_value=mock_client):
        result = await skill.run(metric="steps", timeout=5.0)

    assert result.ok is True
    assert "8,542" in result.message


@pytest.mark.asyncio
async def test_missing_metric(skill):
    result = await skill.run(timeout=5.0)
    assert result.ok is False


@pytest.mark.asyncio
async def test_unknown_metric(skill):
    result = await skill.run(metric="blood_pressure", timeout=5.0)
    assert result.ok is False


@pytest.mark.asyncio
async def test_connection_error(skill):
    with patch.object(skill, "_get_client", side_effect=ConnectionError("API down")):
        result = await skill.run(metric="sleep", timeout=5.0)

    assert result.ok is False
    assert "API down" in result.message
