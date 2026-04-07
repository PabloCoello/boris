"""Music skills via Spotify (spotipy)."""

from __future__ import annotations

import asyncio

from loguru import logger

from boris.skills.base import Skill, SkillResult

SEARCH_TYPES = {"artist", "album", "playlist", "track"}
CONTROL_ACTIONS = {"pause", "next", "prev", "volume"}


class _SpotifyMixin:
    """Shared Spotify client init — prevents credentials in repr."""

    _client_id: str
    _client_secret: str
    _sp = None

    def _get_spotify(self):
        if self._sp is None:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            self._sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self._client_id,
                client_secret=self._client_secret,
                redirect_uri="http://localhost:8888/callback",
                scope="user-modify-playback-state user-read-playback-state",
            ))
            logger.info("Spotify: autenticado")
        return self._sp

    def __repr__(self) -> str:
        return f"{type(self).__name__}(client_id='{self._client_id[:4]}***')"


class MusicPlaySkill(_SpotifyMixin, Skill):
    name = "music_play"
    description = "Reproduce música vía Spotify."

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    async def execute(self, **kwargs) -> SkillResult:
        query = kwargs.get("query")
        if not query:
            return SkillResult(ok=False, message="Falta la búsqueda (query).")

        search_type = kwargs.get("type", "track")
        if search_type not in SEARCH_TYPES:
            search_type = "track"
        return await asyncio.to_thread(self._play, query, search_type)

    def _play(self, query: str, search_type: str) -> SkillResult:
        sp = self._get_spotify()
        results = sp.search(q=query, type=search_type, limit=1)

        key = f"{search_type}s"
        items = results.get(key, {}).get("items", [])
        if not items:
            return SkillResult(ok=False, message=f"No encontré '{query}' en Spotify.")

        item = items[0]
        name = item.get("name", query)
        uri = item.get("uri")
        if not uri:
            return SkillResult(ok=False, message=f"Resultado sin URI para '{query}'.")

        if search_type == "track":
            sp.start_playback(uris=[uri])
        else:
            sp.start_playback(context_uri=uri)

        return SkillResult(ok=True, message=f"Reproduciendo: {name}.")


class MusicControlSkill(_SpotifyMixin, Skill):
    name = "music_control"
    description = "Controla la reproducción de Spotify."

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action")
        if not action:
            return SkillResult(ok=False, message="Falta la acción (pause/next/prev/volume).")
        if action not in CONTROL_ACTIONS:
            return SkillResult(ok=False, message=f"Acción desconocida: '{action}'. Usa: {', '.join(CONTROL_ACTIONS)}.")

        return await asyncio.to_thread(self._control, action, kwargs)

    def _control(self, action: str, kwargs: dict) -> SkillResult:
        sp = self._get_spotify()

        if action == "pause":
            sp.pause_playback()
            return SkillResult(ok=True, message="Reproducción pausada.")
        elif action == "next":
            sp.next_track()
            return SkillResult(ok=True, message="Siguiente canción.")
        elif action == "prev":
            sp.previous_track()
            return SkillResult(ok=True, message="Canción anterior.")
        elif action == "volume":
            try:
                level = int(kwargs.get("level", 50))
            except (TypeError, ValueError):
                return SkillResult(ok=False, message="Nivel de volumen inválido, debe ser un número 0-100.")
            level = max(0, min(100, level))
            sp.volume(level)
            return SkillResult(ok=True, message=f"Volumen ajustado a {level}%.")

        return SkillResult(ok=False, message=f"Acción no implementada: {action}.")
