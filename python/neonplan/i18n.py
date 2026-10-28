"""Minimal bilingual text support (German / English) for messages and the PDF."""

from __future__ import annotations

_lang = "de"


def set_lang(lang: str | None) -> None:
    global _lang
    _lang = "en" if (lang or "").lower().startswith("en") else "de"


def get_lang() -> str:
    return _lang


def _(de: str, en: str) -> str:
    """Pick the text for the current language."""
    return en if _lang == "en" else de
