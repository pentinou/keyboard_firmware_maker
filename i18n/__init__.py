"""i18n — internationalisation de keyboard_firmware_maker.

Fournit tr(), get_language(), set_language() et AVAILABLE_LANGUAGES.
La langue est persistée via QSettings et effective au prochain démarrage.

`tr()` est appelé des centaines de fois à la construction de chaque widget :
la langue courante et le dictionnaire de strings sont donc mémorisés en
mémoire, et le cache est invalidé par `set_language()`.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

LANG_FR = "fr"
LANG_EN = "en"
LANG_IT = "it"

AVAILABLE_LANGUAGES: dict[str, str] = {
    LANG_FR: "Français",
    LANG_EN: "English",
    LANG_IT: "Italiano",
}

_SETTINGS_ORG = "Pentinou"
_SETTINGS_APP = "keyboard_firmware_maker"

# Cache : évite d'instancier un QSettings et de relire le disque à chaque tr().
_lang: str | None = None
_strings: dict[str, str] | None = None
_fallback: dict[str, str] | None = None


def _load_cache() -> None:
    """Résout la langue courante et charge les dictionnaires correspondants."""
    global _lang, _strings, _fallback
    from i18n.translations import STRINGS

    _lang = str(QSettings(_SETTINGS_ORG, _SETTINGS_APP).value("language", LANG_FR))
    _fallback = STRINGS[LANG_FR]
    _strings = STRINGS.get(_lang, _fallback)


def get_language() -> str:
    if _lang is None:
        _load_cache()
    return _lang  # type: ignore[return-value]


def set_language(lang: str) -> None:
    QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue("language", lang)
    _invalidate_cache()


def _invalidate_cache() -> None:
    """Force la relecture de la langue au prochain appel (tests, changement direct)."""
    global _lang, _strings, _fallback
    _lang = _strings = _fallback = None


def tr(key: str) -> str:
    if _strings is None:
        _load_cache()
    value: Any = _strings.get(key)  # type: ignore[union-attr]
    if value is None:
        return _fallback.get(key, key)  # type: ignore[union-attr]
    return value
