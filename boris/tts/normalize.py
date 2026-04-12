"""Normalize text for TTS: convert numbers, times, and symbols to spoken Spanish."""

from __future__ import annotations

import re

_UNITS = [
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
    "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
    "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve",
]

_TENS = [
    "", "", "veinte", "treinta", "cuarenta", "cincuenta",
    "sesenta", "setenta", "ochenta", "noventa",
]

_HUNDREDS = [
    "", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
    "seiscientos", "setecientos", "ochocientos", "novecientos",
]


def _int_to_words(n: int) -> str:
    """Convert integer 0–9999 to Spanish words."""
    if n < 0:
        return "menos " + _int_to_words(-n)
    if n < 30:
        return _UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return _TENS[tens] if unit == 0 else f"{_TENS[tens]} y {_UNITS[unit]}"
    if n == 100:
        return "cien"
    if n < 1000:
        h, rest = divmod(n, 100)
        return _HUNDREDS[h] if rest == 0 else f"{_HUNDREDS[h]} {_int_to_words(rest)}"
    if n < 10000:
        th, rest = divmod(n, 1000)
        prefix = "mil" if th == 1 else f"{_int_to_words(th)} mil"
        return prefix if rest == 0 else f"{prefix} {_int_to_words(rest)}"
    return str(n)


def _time_to_words(match: re.Match) -> str:
    """Convert HH:MM to spoken Spanish."""
    h, m = int(match.group(1)), int(match.group(2))
    h_word = _int_to_words(h)
    if m == 0:
        return h_word
    m_word = _int_to_words(m)
    return f"{h_word} y {m_word}" if m < 30 else f"{h_word} {m_word}"


def _date_dd_mm_to_words(match: re.Match) -> str:
    """Convert DD/MM to spoken Spanish."""
    day = int(match.group(1))
    month = int(match.group(2))
    months = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    m_name = months[month] if 1 <= month <= 12 else str(month)
    return f"{_int_to_words(day)} de {m_name}"


def _number_to_words(match: re.Match) -> str:
    """Convert a standalone number to Spanish words."""
    n = int(match.group(0))
    if 0 <= n <= 9999:
        return _int_to_words(n)
    return match.group(0)


def normalize_for_tts(text: str) -> str:
    """Convert numbers and times in text to spoken Spanish words."""
    # Times: 14:37, 9:00
    text = re.sub(r"\b(\d{1,2}):(\d{2})\b", _time_to_words, text)
    # Dates: 08/04, 25/12
    text = re.sub(r"\b(\d{1,2})/(\d{2})\b", _date_dd_mm_to_words, text)
    # Standalone numbers: 42, 1000
    text = re.sub(r"\b\d+\b", _number_to_words, text)
    return text
