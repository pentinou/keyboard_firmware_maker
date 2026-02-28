"""Tests pour MainWindow — structure des onglets."""
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QDialog, QTabWidget

from models.project_model import ProjectModel
from ui.main_window import MainWindow


def test_main_window_has_four_tabs(qtbot):
    """MainWindow doit avoir exactement 4 onglets dans l'ordre attendu."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)

    tab_widget = window.findChild(QTabWidget)
    assert tab_widget is not None
    assert tab_widget.count() == 4
    assert tab_widget.tabText(0) == "Matériel"
    assert tab_widget.tabText(1) == "OLED"
    assert tab_widget.tabText(2) == "RGB"
    assert tab_widget.tabText(3) == "Build"


def test_main_window_title(qtbot):
    """MainWindow doit avoir un titre approprié."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    assert "keyboard" in window.windowTitle().lower() or "firmware" in window.windowTitle().lower()


def test_main_window_accepts_project_model(qtbot):
    """MainWindow doit stocker le ProjectModel passé via le constructeur."""
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    window = MainWindow(model)
    qtbot.addWidget(window)
    assert window.model is model


def test_oled_tab_enabled_for_sofle(qtbot):
    """L'onglet OLED doit être activé quand le Sofle (oled=True) est sélectionné."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    keyboard_combo = window._tab_hardware.findChild(QTabWidget.__class__, "keyboard_combo")
    from PySide6.QtWidgets import QComboBox
    keyboard_combo = window._tab_hardware.findChild(QComboBox, "keyboard_combo")
    sofle_index = next(
        (i for i in range(keyboard_combo.count()) if "Sofle" in keyboard_combo.itemText(i)),
        None,
    )
    assert sofle_index is not None
    keyboard_combo.setCurrentIndex(sofle_index)
    assert window._tabs.isTabEnabled(1) is True   # OLED
    assert window._tabs.isTabEnabled(2) is True   # RGB


def test_rgb_tab_always_enabled(qtbot):
    """L'onglet RGB est toujours accessible (layout physique visible pour tous les claviers)."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    from PySide6.QtWidgets import QComboBox
    keyboard_combo = window._tab_hardware.findChild(QComboBox, "keyboard_combo")
    corne_index = next(
        (i for i in range(keyboard_combo.count()) if "Corne" in keyboard_combo.itemText(i)),
        None,
    )
    assert corne_index is not None
    keyboard_combo.setCurrentIndex(corne_index)
    assert window._tabs.isTabEnabled(2) is True   # RGB toujours actif
    assert window._tabs.isTabEnabled(1) is True   # OLED toujours actif


def test_tabs_update_dynamically_on_keyboard_change(qtbot):
    """Changer de clavier doit mettre à jour les onglets dynamiquement."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    from PySide6.QtWidgets import QComboBox
    keyboard_combo = window._tab_hardware.findChild(QComboBox, "keyboard_combo")
    # Sélectionner Sofle → OLED + RGB activés
    sofle_index = next(i for i in range(keyboard_combo.count()) if "Sofle" in keyboard_combo.itemText(i))
    keyboard_combo.setCurrentIndex(sofle_index)
    assert window._tabs.isTabEnabled(1) is True
    assert window._tabs.isTabEnabled(2) is True
    # Passer sur Corne → RGB toujours actif (layout physique visible)
    corne_index = next(i for i in range(keyboard_combo.count()) if "Corne" in keyboard_combo.itemText(i))
    keyboard_combo.setCurrentIndex(corne_index)
    assert window._tabs.isTabEnabled(2) is True


def test_build_tab_always_enabled(qtbot):
    """L'onglet Build doit toujours rester activé quelle que soit la sélection."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    from PySide6.QtWidgets import QComboBox
    keyboard_combo = window._tab_hardware.findChild(QComboBox, "keyboard_combo")
    for i in range(keyboard_combo.count()):
        keyboard_combo.setCurrentIndex(i)
        assert window._tabs.isTabEnabled(3) is True, f"Onglet Build désactivé pour clavier index {i}"


def test_main_window_has_file_menu(qtbot):
    """Le menu Fichier doit être présent dans la barre de menus."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    menu_bar = window.menuBar()
    menus = [menu_bar.actions()[i].text() for i in range(len(menu_bar.actions()))]
    assert "Fichier" in menus


def test_file_menu_has_save_action(qtbot):
    """Le menu Fichier doit contenir une action Sauvegarder."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    file_action = next(a for a in window.menuBar().actions() if a.text() == "Fichier")
    file_menu = file_action.menu()
    action_texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
    assert any("Sauvegarder" in t for t in action_texts)


def test_file_menu_has_open_action(qtbot):
    """Le menu Fichier doit contenir une action Ouvrir."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    file_action = next(a for a in window.menuBar().actions() if a.text() == "Fichier")
    file_menu = file_action.menu()
    action_texts = [a.text() for a in file_menu.actions() if not a.isSeparator()]
    assert any("Ouvrir" in t for t in action_texts)


def test_open_project_syncs_oled_overlays(qtbot, tmp_path):
    """L4/M1 — _open_project() doit synchroniser les checkboxes overlay d'OledWidget."""
    from modules.project_manager.file_io import save_project
    from PySide6.QtWidgets import QCheckBox
    model = ProjectModel()
    model.oled.left.layer.enabled = True
    model.oled.left.wpm.enabled = True
    proj_path = tmp_path / "proj.kfm.json"
    save_project(model, proj_path)

    window = MainWindow(ProjectModel())
    qtbot.addWidget(window)
    with patch("ui.main_window.QFileDialog.getOpenFileName", return_value=(str(proj_path), "")):
        window._open_project()

    cb_layer = window._tab_oled.findChild(QCheckBox, "left_layer_check")
    cb_wpm = window._tab_oled.findChild(QCheckBox, "left_wpm_check")
    cb_caps = window._tab_oled.findChild(QCheckBox, "left_caps_check")
    assert cb_layer.isChecked()
    assert cb_wpm.isChecked()
    assert not cb_caps.isChecked()


def test_open_project_syncs_rgb_per_key(qtbot, tmp_path):
    """L4/M1 — _open_project() doit synchroniser les couleurs per-key de RgbWidget."""
    from modules.project_manager.file_io import save_project
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.rgb.per_key["L_r0_c0"] = "#FF0000"
    proj_path = tmp_path / "proj_rgb.kfm.json"
    save_project(model, proj_path)

    window = MainWindow(ProjectModel())
    qtbot.addWidget(window)
    with patch("ui.main_window.QFileDialog.getOpenFileName", return_value=(str(proj_path), "")):
        window._open_project()

    assert "#FF0000" in window._tab_rgb._key_buttons["L_r0_c0"].styleSheet()


def test_initial_tab_state_reflects_default_keyboard_capabilities(qtbot):
    """L2/L3 — Les onglets OLED/RGB reflètent les capacités du clavier par défaut dès l'init."""
    model = ProjectModel()
    window = MainWindow(model)
    qtbot.addWidget(window)
    from config import KEYBOARDS_DIR
    from modules.hardware.keyboard_loader import load_all_keyboards
    keyboards = load_all_keyboards(KEYBOARDS_DIR)
    default_idx = window._tab_hardware._keyboard_combo.currentIndex()
    if keyboards and 0 <= default_idx < len(keyboards):
        default_kb = keyboards[default_idx]
        assert window._tabs.isTabEnabled(1) == bool(default_kb.capabilities.get("oled", False))
        assert window._tabs.isTabEnabled(2) is True  # RGB toujours actif


def test_open_project_preserves_mcu_selection(qtbot, tmp_path):
    """L4/M1 — _open_project() doit restaurer le MCU sauvegardé, pas le premier de la liste."""
    import pytest
    from modules.project_manager.file_io import save_project
    from config import KEYBOARDS_DIR
    from modules.hardware.keyboard_loader import load_all_keyboards
    keyboards = load_all_keyboards(KEYBOARDS_DIR)
    corne = next((kb for kb in keyboards if kb.model == "corne"), None)
    if corne is None or len(corne.mcu_options) < 2:
        pytest.skip("Le Corne n'a pas au moins 2 MCU options")
    target_mcu = corne.mcu_options[1].id  # deuxième MCU (elite_c)
    model = ProjectModel()
    model.keyboard.model = "corne"
    model.keyboard.mcu = target_mcu
    proj_path = tmp_path / "proj_mcu.kfm.json"
    save_project(model, proj_path)
    window = MainWindow(ProjectModel())
    qtbot.addWidget(window)
    with patch("ui.main_window.QFileDialog.getOpenFileName", return_value=(str(proj_path), "")):
        window._open_project()
    assert window.model.keyboard.mcu == target_mcu


def test_check_vial_qmk_shows_warning_on_rejection(qtbot):
    """M3 — Un avertissement est affiché si le dialogue Vial-QMK est rejeté."""
    model = ProjectModel()
    with patch("ui.main_window.VialQmkManager.is_ready", return_value=False):
        with patch("ui.main_window.VialQmkSetupDialog") as mock_dlg_cls:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = QDialog.DialogCode.Rejected
            mock_dlg_cls.return_value = mock_dlg
            with patch("ui.main_window.QMessageBox.warning") as mock_warn:
                window = MainWindow(model)
                qtbot.addWidget(window)
    mock_warn.assert_called_once()


def test_check_vial_qmk_no_warning_on_acceptance(qtbot):
    """M3 — Aucun avertissement si le dialogue Vial-QMK est accepté."""
    model = ProjectModel()
    with patch("ui.main_window.VialQmkManager.is_ready", return_value=False):
        with patch("ui.main_window.VialQmkSetupDialog") as mock_dlg_cls:
            mock_dlg = MagicMock()
            mock_dlg.exec.return_value = QDialog.DialogCode.Accepted
            mock_dlg_cls.return_value = mock_dlg
            with patch("ui.main_window.QMessageBox.warning") as mock_warn:
                window = MainWindow(model)
                qtbot.addWidget(window)
    mock_warn.assert_not_called()
