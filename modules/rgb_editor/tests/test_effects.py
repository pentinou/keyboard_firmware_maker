"""Tests pour modules/rgb_editor/effects.py."""
from __future__ import annotations

from modules.rgb_editor.effects import EFFECT_TYPES


def test_effect_types_is_immutable_sequence():
    """L1 — EFFECT_TYPES doit être un tuple immuable pour éviter toute mutation accidentelle."""
    assert isinstance(EFFECT_TYPES, tuple)


def test_effect_types_has_at_least_two():
    assert len(EFFECT_TYPES) >= 2


def test_effect_types_contains_static():
    ids = [et[0] for et in EFFECT_TYPES]
    assert "static" in ids


def test_effect_types_contains_ripple():
    ids = [et[0] for et in EFFECT_TYPES]
    assert "ripple" in ids


def test_effect_types_ids_are_snake_case():
    for effect_id, _ in EFFECT_TYPES:
        assert effect_id == effect_id.lower()
        assert " " not in effect_id


def test_effect_types_have_display_names():
    for _, display in EFFECT_TYPES:
        assert len(display) > 0


def test_no_qt_import_in_effects():
    from pathlib import Path
    source = Path(__file__).parent.parent / "effects.py"
    content = source.read_text(encoding="utf-8")
    assert "PySide6" not in content
    assert "PyQt" not in content
