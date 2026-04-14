"""Conftest pour les tests keyboard_editor nécessitant Qt."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Fournit une QApplication unique pour toute la session de tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
