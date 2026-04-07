"""Google Calendar skill — read upcoming events."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

from boris.skills.base import Skill, SkillResult


class CalendarSkill(Skill):
    name = "calendar"
    description = "Eventos próximos de Google Calendar."

    def __init__(self, credentials_json: str):
        self._credentials_path = Path(credentials_json)
        self._token_path = self._credentials_path.parent / "google-token.json"
        self._service = None

    def __repr__(self) -> str:
        return f"CalendarSkill(credentials='{self._credentials_path}')"

    def _get_service(self):
        """Lazy-init Google Calendar API service."""
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

        creds = None
        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self._credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            self._token_path.write_text(creds.to_json())
            logger.info("Google Calendar: token guardado")

        self._service = build("calendar", "v3", credentials=creds)
        logger.info("Google Calendar: servicio inicializado")
        return self._service

    async def execute(self, **kwargs) -> SkillResult:
        days = kwargs.get("days", 7)
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 7

        return await asyncio.to_thread(self._fetch_events, days)

    def _fetch_events(self, days: int) -> SkillResult:
        try:
            service = self._get_service()
        except FileNotFoundError:
            return SkillResult(
                ok=False,
                message=f"No se encontró {self._credentials_path}. Ver docs/oauth-setup.md.",
            )
        except Exception as e:
            logger.error(f"Calendar auth error: {e}")
            return SkillResult(ok=False, message=f"Error de autenticación: {e}")

        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days)

        try:
            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now.isoformat(),
                    timeMax=time_max.isoformat(),
                    maxResults=20,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except Exception as e:
            logger.error(f"Calendar API error: {e}")
            return SkillResult(ok=False, message=f"Error al consultar calendario: {e}")

        events = result.get("items", [])
        if not events:
            return SkillResult(ok=True, message=f"No hay eventos en los próximos {days} días.")

        lines = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            summary = event.get("summary", "(sin título)")
            # Format datetime nicely
            if "T" in start:
                dt = datetime.fromisoformat(start)
                formatted = dt.strftime("%d/%m %H:%M")
            else:
                formatted = start
            lines.append(f"- {formatted}: {summary}")

        return SkillResult(
            ok=True,
            message=f"Eventos próximos ({days} días):\n" + "\n".join(lines),
        )


async def _auth():
    """CLI entry point: authenticate with Google Calendar."""
    import sys

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    from boris.config import load_config

    config = load_config()
    creds_path = config.secrets.google_credentials_json
    if not creds_path:
        logger.error("GOOGLE_CREDENTIALS_JSON no configurado en .env")
        return

    skill = CalendarSkill(creds_path)
    skill._get_service()
    logger.info("Autenticación completada con éxito.")


if __name__ == "__main__":
    asyncio.run(_auth())
