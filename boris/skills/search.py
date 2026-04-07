"""Web search skill via SearXNG."""

from __future__ import annotations

import aiohttp

from boris.skills.base import Skill, SkillResult

MAX_RESULTS = 3


class SearchSkill(Skill):
    name = "search"
    description = "Búsqueda web vía SearXNG."

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    async def execute(self, **kwargs) -> SkillResult:
        query = kwargs.get("query")
        if not query:
            return SkillResult(ok=False, message="Falta la consulta de búsqueda (query).")

        url = f"{self._base_url}/search"
        params = {"q": query, "format": "json", "language": "es"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return SkillResult(ok=False, message=f"SearXNG respondió con error {resp.status}.")

                data = await resp.json()

        results = data.get("results", [])[:MAX_RESULTS]
        if not results:
            return SkillResult(ok=True, message="No se encontraron resultados.")

        snippets = [
            f"- {r.get('title', 'Sin título')}: {r.get('content', 'Sin contenido')}"
            for r in results
        ]
        return SkillResult(ok=True, message="Resultados:\n" + "\n".join(snippets))
