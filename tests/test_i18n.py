"""Tests du cache de traduction — i18n/__init__.py.

`tr()` instanciait un QSettings et ré-importait le dictionnaire à chaque appel
(~28 µs), pour 338 sites d'appel rejoués à chaque reconstruction d'UI.
Le cache doit rester correct quand la langue change.
"""
from __future__ import annotations

import pytest

from i18n import LANG_EN, LANG_FR, LANG_IT, get_language, set_language, tr


@pytest.fixture(autouse=True)
def restore_language():
    """La langue est persistée dans QSettings : ne pas polluer la config réelle."""
    original = get_language()
    yield
    set_language(original)


def test_tr_returns_french_by_default():
    set_language(LANG_FR)
    assert tr("menu.file") == "Fichier"


def test_set_language_invalidates_cache():
    set_language(LANG_FR)
    assert tr("menu.file") == "Fichier"
    set_language(LANG_EN)
    assert tr("menu.file") == "File"
    set_language(LANG_IT)
    assert tr("tab.hardware") == "Hardware"


def test_get_language_reflects_set_language():
    set_language(LANG_EN)
    assert get_language() == LANG_EN


def test_unknown_key_returns_key_itself():
    set_language(LANG_FR)
    assert tr("cle.inexistante") == "cle.inexistante"


def test_missing_translation_falls_back_to_french(monkeypatch):
    """Une clé absente d'une langue retombe sur le français, pas sur la clé brute."""
    import i18n
    from i18n.translations import STRINGS

    monkeypatch.setitem(STRINGS, "en", {k: v for k, v in STRINGS["en"].items() if k != "menu.file"})
    set_language(LANG_EN)
    i18n._invalidate_cache()

    assert tr("menu.file") == "Fichier"


def test_unknown_language_falls_back_to_french():
    set_language("de")
    assert tr("menu.file") == "Fichier"
