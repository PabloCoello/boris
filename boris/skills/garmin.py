"""Garmin health data skill via garminconnect."""

from __future__ import annotations

import asyncio
from datetime import date

from loguru import logger

from boris.skills.base import Skill, SkillResult

SUPPORTED_METRICS = {"sleep", "hrv", "steps", "battery", "activity"}


class GarminSkill(Skill):
    name = "garmin"
    description = "Datos de salud desde Garmin Connect."

    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._client = None

    def __repr__(self) -> str:
        return f"GarminSkill(email='{self._email[:3]}***')"

    def _get_client(self):
        """Lazy-init Garmin client (login is expensive)."""
        if self._client is None:
            from garminconnect import Garmin

            self._client = Garmin(self._email, self._password)
            self._client.login()
            logger.info("Garmin: login exitoso")
        return self._client

    async def execute(self, **kwargs) -> SkillResult:
        metric = kwargs.get("metric")
        if not metric:
            return SkillResult(ok=False, message="Falta la métrica (sleep/hrv/steps/battery/activity).")
        if metric not in SUPPORTED_METRICS:
            return SkillResult(ok=False, message=f"Métrica desconocida: '{metric}'. Usa: {', '.join(SUPPORTED_METRICS)}.")

        handler = getattr(self, f"_get_{metric}", None)
        if handler is None:
            return SkillResult(ok=False, message=f"Métrica '{metric}' no implementada.")

        return await asyncio.to_thread(handler)

    def _get_sleep(self) -> SkillResult:
        client = self._get_client()
        today = date.today().isoformat()
        data = client.get_sleep_data(today)

        sleep_dto = data.get("dailySleepDTO", {})
        total_s = sleep_dto.get("sleepTimeSeconds", 0)
        deep_s = sleep_dto.get("deepSleepSeconds", 0)
        light_s = sleep_dto.get("lightSleepSeconds", 0)
        rem_s = sleep_dto.get("remSleepSeconds", 0)
        awake_s = sleep_dto.get("awakeSleepSeconds", 0)

        def fmt(seconds: int) -> str:
            h, m = divmod(seconds // 60, 60)
            return f"{h}h {m}m"

        return SkillResult(
            ok=True,
            message=(
                f"Sueño: {fmt(total_s)} total — "
                f"profundo {fmt(deep_s)}, ligero {fmt(light_s)}, "
                f"REM {fmt(rem_s)}, despierto {fmt(awake_s)}."
            ),
        )

    def _get_steps(self) -> SkillResult:
        client = self._get_client()
        today = date.today().isoformat()
        data = client.get_stats(today)

        steps = data.get("totalSteps", 0)
        distance_m = data.get("totalDistanceMeters", 0)
        distance_km = distance_m / 1000

        return SkillResult(
            ok=True,
            message=f"Pasos hoy: {steps:,} ({distance_km:.1f} km).",
        )

    def _get_hrv(self) -> SkillResult:
        client = self._get_client()
        today = date.today().isoformat()
        data = client.get_hrv_data(today)

        summary = data.get("hrvSummary", {})
        weekly_avg = summary.get("weeklyAvg", 0)
        last_night = summary.get("lastNight", 0)

        return SkillResult(
            ok=True,
            message=f"HRV: última noche {last_night}ms, media semanal {weekly_avg}ms.",
        )

    def _get_battery(self) -> SkillResult:
        client = self._get_client()
        today = date.today().isoformat()
        data = client.get_body_battery(today)

        entries = data if isinstance(data, list) else data.get("bodyBatteryValuesArray", [])
        if entries:
            latest = entries[-1]
            value = latest[-1] if isinstance(latest, list) else latest.get("bodyBatteryValue", "?")
        else:
            value = "sin datos"

        return SkillResult(ok=True, message=f"Body Battery actual: {value}.")

    def _get_activity(self) -> SkillResult:
        client = self._get_client()
        activities = client.get_activities(0, 3)

        if not activities:
            return SkillResult(ok=True, message="No hay actividades recientes.")

        lines = []
        for a in activities[:3]:
            name = a.get("activityName", "Actividad")
            duration_m = a.get("duration", 0) / 60
            distance_km = (a.get("distance", 0) or 0) / 1000
            lines.append(f"- {name}: {duration_m:.0f}min, {distance_km:.1f}km")

        return SkillResult(ok=True, message="Actividades recientes:\n" + "\n".join(lines))
