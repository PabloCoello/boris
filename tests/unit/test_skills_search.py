"""Tests for boris.skills.search module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from boris.skills.search import SearchSkill


def _mock_session(json_data, status=200):
    """Create a mock aiohttp session with the given response."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return mock_session


@pytest.mark.asyncio
async def test_search_returns_results():
    skill = SearchSkill(base_url="http://localhost:8080")

    session = _mock_session({
        "results": [
            {"title": "Asturias", "content": "Asturias tiene 1 millón de habitantes."},
            {"title": "Wiki", "content": "Comunidad autónoma del norte de España."},
        ]
    })

    with patch("boris.skills.search.aiohttp.ClientSession", return_value=session):
        result = await skill.run(query="habitantes Asturias", timeout=5.0)

    assert result.ok is True
    assert "Asturias" in result.message


@pytest.mark.asyncio
async def test_search_missing_query():
    skill = SearchSkill(base_url="http://localhost:8080")
    result = await skill.run(timeout=5.0)
    assert result.ok is False


@pytest.mark.asyncio
async def test_search_no_results():
    skill = SearchSkill(base_url="http://localhost:8080")

    session = _mock_session({"results": []})

    with patch("boris.skills.search.aiohttp.ClientSession", return_value=session):
        result = await skill.run(query="xyznonexistent", timeout=5.0)

    assert result.ok is True
    assert "no se encontraron" in result.message.lower()


@pytest.mark.asyncio
async def test_search_http_error():
    skill = SearchSkill(base_url="http://localhost:8080")

    session = _mock_session({}, status=500)

    with patch("boris.skills.search.aiohttp.ClientSession", return_value=session):
        result = await skill.run(query="test", timeout=5.0)

    assert result.ok is False
    assert "500" in result.message
