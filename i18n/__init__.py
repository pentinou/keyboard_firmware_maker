"""i18n — internationalisation de keyboard_firmware_maker.

Fournit tr(), get_language(), set_language() et AVAILABLE_LANGUAGES.
La langue est persistée via QSettings et effective au prochain démarrage.
"""
from __future__ import annotations

from PySide6.QtCore import QSettings

LANG_FR = "fr"
LANG_EN = "en"
LANG_IT = "it"

AVAILABLE_LANGUAGES: dict[str, str] = {
    LANG_FR: "Français",
    LANG_EN: "English",
    LANG_IT: "Italiano",
}


def get_language() -> str:
    return str(QSettings("Pentinou", "keyboard_firmware_maker").value("language", LANG_FR))


def set_language(lang: str) -> None:
    QSettings("Pentinou", "keyboard_firmware_maker").setValue("language", lang)


def tr(key: str) -> str:
    from i18n.translations import STRINGS
    lang = get_language()
    d = STRINGS.get(lang, STRINGS[LANG_FR])
    return d.get(key, STRINGS[LANG_FR].get(key, key))
