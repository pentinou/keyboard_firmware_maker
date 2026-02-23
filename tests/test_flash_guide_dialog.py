"""Tests pour ui/widgets/flash_guide_dialog.py — Story 4.4."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QStackedWidget, QLabel, QPushButton

from ui.widgets.flash_guide_dialog import FLASH_GUIDE_STEPS, FlashGuideDialog, ASSETS_DIR


# ──────────────────────────────────────────────────── FlashGuideDialog ──


class TestFlashGuideDialogCreation:
    @pytest.fixture
    def dialog(self, qtbot):
        dlg = FlashGuideDialog()
        qtbot.addWidget(dlg)
        return dlg

    def test_dialog_created(self, dialog):
        assert dialog is not None

    def test_has_4_steps(self, dialog):
        stack = dialog.findChild(QStackedWidget, "flash_guide_stack")
        assert stack is not None
        assert stack.count() == 4

    def test_starts_at_step_0(self, dialog):
        stack = dialog.findChild(QStackedWidget, "flash_guide_stack")
        assert stack.currentIndex() == 0

    def test_title_label_shows_step_1(self, dialog):
        lbl = dialog.findChild(QLabel, "lbl_step_title")
        assert lbl is not None
        assert "1" in lbl.text() or "BOOT" in lbl.text()

    def test_progress_label_shows_step_1_of_4(self, dialog):
        lbl = dialog.findChild(QLabel, "lbl_step_progress")
        assert lbl is not None
        assert "1" in lbl.text()
        assert "4" in lbl.text()

    def test_prev_button_disabled_at_step_0(self, dialog):
        btn = dialog.findChild(QPushButton, "btn_prev")
        assert btn is not None
        assert not btn.isEnabled()

    def test_next_button_visible_at_step_0(self, dialog):
        btn = dialog.findChild(QPushButton, "btn_next")
        assert btn is not None
        # isVisible() est False en headless (parent non affiché) → on teste isHidden()
        assert not btn.isHidden()

    def test_close_button_hidden_at_step_0(self, dialog):
        btn = dialog.findChild(QPushButton, "btn_close")
        assert btn is not None
        # Cohérent avec test_last_step_shows_close : on teste isHidden()
        assert btn.isHidden()


class TestFlashGuideNavigation:
    @pytest.fixture
    def dialog(self, qtbot):
        dlg = FlashGuideDialog()
        qtbot.addWidget(dlg)
        return dlg

    def test_next_goes_to_step_1(self, dialog, qtbot):
        from PySide6.QtCore import Qt
        btn_next = dialog.findChild(QPushButton, "btn_next")
        qtbot.mouseClick(btn_next, Qt.LeftButton)
        stack = dialog.findChild(QStackedWidget, "flash_guide_stack")
        assert stack.currentIndex() == 1

    def test_prev_enabled_after_next(self, dialog, qtbot):
        from PySide6.QtCore import Qt
        btn_next = dialog.findChild(QPushButton, "btn_next")
        qtbot.mouseClick(btn_next, Qt.LeftButton)
        btn_prev = dialog.findChild(QPushButton, "btn_prev")
        assert btn_prev.isEnabled()

    def test_navigate_to_last_step(self, dialog):
        # Navigate to last step programmatically
        dialog._go_to_step(3)
        stack = dialog.findChild(QStackedWidget, "flash_guide_stack")
        assert stack.currentIndex() == 3

    def test_last_step_hides_next(self, dialog):
        dialog._go_to_step(3)
        btn_next = dialog.findChild(QPushButton, "btn_next")
        assert btn_next.isHidden()

    def test_last_step_shows_close(self, dialog):
        dialog._go_to_step(3)
        btn_close = dialog.findChild(QPushButton, "btn_close")
        assert not btn_close.isHidden()

    def test_last_step_title_contains_step4(self, dialog):
        dialog._go_to_step(3)
        lbl = dialog.findChild(QLabel, "lbl_step_title")
        assert "4" in lbl.text() or "firmware" in lbl.text().lower()

    def test_go_back_from_step_2_to_1(self, dialog):
        dialog._go_to_step(2)
        dialog._on_prev()
        stack = dialog.findChild(QStackedWidget, "flash_guide_stack")
        assert stack.currentIndex() == 1

    def test_progress_updates_on_navigation(self, dialog):
        dialog._go_to_step(1)
        lbl = dialog.findChild(QLabel, "lbl_step_progress")
        assert "2" in lbl.text()

    def test_navigate_all_steps(self, dialog):
        """Vérifier que les 4 étapes s'enchaînent sans erreur."""
        for i in range(4):
            dialog._go_to_step(i)
            stack = dialog.findChild(QStackedWidget, "flash_guide_stack")
            assert stack.currentIndex() == i

    def test_prev_noop_at_step_0(self, dialog):
        """_on_prev à l'étape 0 ne doit pas crasher ni aller en négatif."""
        dialog._on_prev()
        assert dialog._current == 0

    def test_next_noop_at_last_step(self, dialog):
        dialog._go_to_step(3)
        dialog._on_next()
        assert dialog._current == 3

    def test_go_to_step_out_of_bounds_noop(self, dialog):
        """_go_to_step avec index hors borne ne doit pas crasher (L1)."""
        dialog._go_to_step(0)
        dialog._go_to_step(-1)   # silently ignored
        assert dialog._current == 0
        dialog._go_to_step(99)   # silently ignored
        assert dialog._current == 0


class TestFlashGuideAssets:
    @pytest.fixture
    def dialog(self, qtbot):
        dlg = FlashGuideDialog()
        qtbot.addWidget(dlg)
        return dlg

    def test_assets_dir_is_local(self):
        """ASSETS_DIR doit pointer vers le disque local (FR29 — pas de réseau)."""
        assert ASSETS_DIR.is_absolute()
        assert "flash_guide" in str(ASSETS_DIR)

    def test_all_step_images_exist(self):
        """Les 4 images placeholder doivent exister localement."""
        for step in FLASH_GUIDE_STEPS:
            img_path = ASSETS_DIR / step["image"]
            assert img_path.exists(), f"Image manquante : {img_path}"

    def test_flash_guide_steps_count(self):
        assert len(FLASH_GUIDE_STEPS) == 4

    def test_each_step_has_required_keys(self):
        for step in FLASH_GUIDE_STEPS:
            assert "title" in step
            assert "text" in step
            assert "image" in step

    def test_images_are_png(self):
        for step in FLASH_GUIDE_STEPS:
            assert step["image"].endswith(".png")

    def test_missing_image_shows_fallback_text(self, qtbot):
        """Si une image est introuvable, le label affiche le texte de fallback (L4)."""
        from ui.widgets.flash_guide_dialog import _make_step_page
        step = {"title": "Test", "text": "desc", "image": "nonexistent_image.png"}
        page = _make_step_page(step)
        qtbot.addWidget(page)
        lbl = page.findChild(QLabel, "lbl_img_nonexistent_image.png")
        assert lbl is not None
        assert "manquante" in lbl.text() or "nonexistent_image.png" in lbl.text()


# ────────────────────────────────────────────── BuildWidget export/guide ──


class TestBuildWidgetExport:
    @pytest.fixture
    def widget(self, qtbot):
        from modules.build_manager.widget import BuildWidget
        from models.project_model import ProjectModel
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        w = BuildWidget(m)
        qtbot.addWidget(w)
        return w

    def test_btn_export_exists(self, widget):
        assert widget._btn_export is not None

    def test_btn_export_disabled_initially(self, widget):
        assert not widget._btn_export.isEnabled()

    def test_btn_export_enabled_after_build_success(self, widget, tmp_path):
        uf2 = tmp_path / "firmware.uf2"
        uf2.write_bytes(b"\x00" * 512)
        widget._on_build_success(str(uf2))
        assert widget._btn_export.isEnabled()

    def test_last_uf2_stored_after_build_success(self, widget, tmp_path):
        uf2 = tmp_path / "firmware.uf2"
        uf2.write_bytes(b"\x00" * 512)
        widget._on_build_success(str(uf2))
        assert widget._last_uf2 == str(uf2)

    def test_export_calls_shutil_copy2(self, widget, tmp_path):
        """_on_export_clicked doit appeler shutil.copy2 avec src et dest."""
        src = tmp_path / "firmware.uf2"
        src.write_bytes(b"\x00" * 512)
        widget._last_uf2 = str(src)
        dest = str(tmp_path / "export" / "firmware.uf2")

        with patch("modules.build_manager.widget.QFileDialog.getSaveFileName",
                   return_value=(dest, "")):
            with patch("modules.build_manager.widget.shutil.copy2") as mock_copy:
                with patch("modules.build_manager.widget.QMessageBox.information"):
                    widget._on_export_clicked()

        mock_copy.assert_called_once()
        args = mock_copy.call_args[0]
        assert args[0] == src
        assert args[1] == dest

    def test_export_noop_when_no_uf2(self, widget):
        """_on_export_clicked sans uf2 ne doit pas crasher."""
        widget._last_uf2 = None
        widget._on_export_clicked()  # no exception

    def test_export_noop_on_dialog_cancel(self, widget, tmp_path):
        src = tmp_path / "firmware.uf2"
        src.write_bytes(b"\x00" * 512)
        widget._last_uf2 = str(src)

        with patch("modules.build_manager.widget.QFileDialog.getSaveFileName",
                   return_value=("", "")):
            with patch("modules.build_manager.widget.shutil.copy2") as mock_copy:
                widget._on_export_clicked()

        mock_copy.assert_not_called()

    def test_btn_guide_exists(self, widget):
        assert widget._btn_guide is not None

    def test_guide_button_always_enabled(self, widget):
        """Le bouton guide est toujours accessible, même sans compilation."""
        assert widget._btn_guide.isEnabled()

    def test_export_fails_gracefully_on_oserror(self, widget, tmp_path):
        """M1 — OSError pendant copy2 affiche QMessageBox.critical sans crash."""
        src = tmp_path / "firmware.uf2"
        src.write_bytes(b"\x00" * 512)
        widget._last_uf2 = str(src)

        with patch("modules.build_manager.widget.QFileDialog.getSaveFileName",
                   return_value=(str(tmp_path / "out.uf2"), "")):
            with patch("modules.build_manager.widget.shutil.copy2",
                       side_effect=OSError("permission denied")):
                with patch("modules.build_manager.widget.QMessageBox.critical") as mock_err:
                    widget._on_export_clicked()

        mock_err.assert_called_once()

    def test_export_warns_when_source_missing(self, widget, tmp_path):
        """M2 — Si le .uf2 source n'existe plus, avertissement + désactivation du bouton."""
        widget._last_uf2 = str(tmp_path / "gone.uf2")  # fichier inexistant
        widget._btn_export.setEnabled(True)

        with patch("modules.build_manager.widget.QMessageBox.warning") as mock_warn:
            widget._on_export_clicked()

        mock_warn.assert_called_once()
        assert not widget._btn_export.isEnabled()
        assert widget._last_uf2 is None

    def test_guide_opens_flash_guide_dialog(self, widget, qtbot):
        # On mocke la classe entière pour éviter l'instanciation Qt en headless
        with patch("ui.widgets.flash_guide_dialog.FlashGuideDialog") as mock_cls:
            mock_cls.return_value.exec.return_value = 0
            widget._on_guide_clicked()
        mock_cls.assert_called_once_with(widget)
        mock_cls.return_value.exec.assert_called_once()
