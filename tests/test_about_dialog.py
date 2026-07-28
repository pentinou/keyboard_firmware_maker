"""Tests pour AboutDialog — version et lien GitHub."""

from ui.widgets.about_dialog import AboutDialog


def test_about_dialog_shows_version(qtbot):
    """AboutDialog doit afficher la version 0.1.0."""
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert "0.1.0" in dialog.windowTitle() or _dialog_contains_text(dialog, "0.1.0")


def _dialog_contains_text(dialog, text: str) -> bool:
    """Vérifie si un texte apparaît dans l'un des QLabel du dialogue."""
    from PySide6.QtWidgets import QLabel
    for label in dialog.findChildren(QLabel):
        if text in label.text():
            return True
    return False


def test_about_dialog_has_github_link(qtbot):
    """AboutDialog doit mentionner un lien GitHub."""
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert _dialog_contains_text(dialog, "github") or _dialog_contains_text(dialog, "GitHub")
