"""Tests de l'application des infobulles — ui/tooltips.py."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QCheckBox, QWidget

from ui.tooltips import apply_tooltips, tooltip_for


def test_known_field_returns_its_text():
    assert "Exemple" in tooltip_for("adv_nkro_enabled")


def test_unknown_field_returns_empty_string():
    assert tooltip_for("champ_sans_infobulle") == ""


@pytest.fixture
def container(qtbot) -> QWidget:
    root = QWidget()
    qtbot.addWidget(root)
    child = QCheckBox(root)
    child.setObjectName("adv_nkro_enabled")
    return root


def test_applies_tooltip_to_named_child(container):
    applied = apply_tooltips(container, ["adv_nkro_enabled"])

    assert applied == 1
    assert container.findChild(QCheckBox, "adv_nkro_enabled").toolTip()


def test_missing_child_is_ignored(container):
    """Un onglet peut ne pas construire tous ses champs selon le clavier."""
    applied = apply_tooltips(container, ["adv_nkro_enabled", "champ_absent"])

    assert applied == 1
