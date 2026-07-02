"""Verrouille la parité des clés de traduction FR/EN/IT.

La langue de référence est le français (langue de fallback de tr()).
Toute clé ajoutée dans une langue doit exister dans les trois.
"""
from i18n import AVAILABLE_LANGUAGES
from i18n.translations import STRINGS


def test_all_available_languages_present_in_strings():
    for lang in AVAILABLE_LANGUAGES:
        assert lang in STRINGS, f"Langue '{lang}' déclarée mais absente de STRINGS"


def test_all_languages_have_same_keys_as_fr():
    reference = set(STRINGS["fr"])
    for lang, strings in STRINGS.items():
        missing = reference - set(strings)
        extra = set(strings) - reference
        assert not missing, f"{lang}: clés manquantes vs fr : {sorted(missing)}"
        assert not extra, f"{lang}: clés en trop vs fr : {sorted(extra)}"


def test_no_empty_translation_values():
    for lang, strings in STRINGS.items():
        empty = [k for k, v in strings.items() if not str(v).strip()]
        assert not empty, f"{lang}: valeurs vides : {empty}"
