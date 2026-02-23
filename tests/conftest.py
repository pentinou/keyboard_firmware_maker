"""Fixtures globales pour les tests de MainWindow.

Auto-patch VialQmkManager.is_ready → True pour éviter le téléchargement
Vial-QMK lors de l'instanciation de MainWindow dans les tests.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _mock_vial_qmk_ready():
    """Toujours simuler Vial-QMK présent dans les tests tests/ (évite téléchargement)."""
    with patch("modules.build_manager.vial_qmk_manager.VialQmkManager.is_ready", return_value=True):
        yield
