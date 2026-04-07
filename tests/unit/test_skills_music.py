"""Tests for boris.skills.music module."""

from unittest.mock import MagicMock, patch

import pytest

from boris.skills.music import MusicControlSkill, MusicPlaySkill


@pytest.fixture
def play_skill():
    return MusicPlaySkill(client_id="fake_id", client_secret="fake_secret")


@pytest.fixture
def control_skill():
    return MusicControlSkill(client_id="fake_id", client_secret="fake_secret")


@pytest.mark.asyncio
async def test_play_artist(play_skill):
    mock_sp = MagicMock()
    mock_sp.search.return_value = {
        "artists": {"items": [{"name": "Rosalía", "uri": "spotify:artist:123"}]}
    }
    mock_sp.devices.return_value = {"devices": [{"id": "dev1", "is_active": True}]}

    with patch.object(play_skill, "_get_spotify", return_value=mock_sp):
        result = await play_skill.run(query="Rosalía", type="artist", timeout=5.0)

    assert result.ok is True
    assert "Rosalía" in result.message


@pytest.mark.asyncio
async def test_play_missing_query(play_skill):
    result = await play_skill.run(timeout=5.0)
    assert result.ok is False


@pytest.mark.asyncio
async def test_play_no_results(play_skill):
    mock_sp = MagicMock()
    mock_sp.search.return_value = {"tracks": {"items": []}}

    with patch.object(play_skill, "_get_spotify", return_value=mock_sp):
        result = await play_skill.run(query="xyznonexistent", timeout=5.0)

    assert result.ok is False
    assert "no encontr" in result.message.lower()


@pytest.mark.asyncio
async def test_control_pause(control_skill):
    mock_sp = MagicMock()

    with patch.object(control_skill, "_get_spotify", return_value=mock_sp):
        result = await control_skill.run(action="pause", timeout=5.0)

    assert result.ok is True
    mock_sp.pause_playback.assert_called_once()


@pytest.mark.asyncio
async def test_control_next(control_skill):
    mock_sp = MagicMock()

    with patch.object(control_skill, "_get_spotify", return_value=mock_sp):
        result = await control_skill.run(action="next", timeout=5.0)

    assert result.ok is True
    mock_sp.next_track.assert_called_once()


@pytest.mark.asyncio
async def test_control_unknown_action(control_skill):
    result = await control_skill.run(action="rewind", timeout=5.0)
    assert result.ok is False
