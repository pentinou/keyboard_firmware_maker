"""Tests pytest-qt pour modules/build_manager/widget.py — BuildWidget.

Couvre l'annulation d'une compilation en cours : les workers exposaient déjà
`stop()` mais aucun élément d'UI ne l'appelait, et `cleanup()` n'était jamais
invoqué à la fermeture de l'application.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QPushButton

from models.project_model import ProjectModel
from modules.build_manager.widget import BuildWidget


@pytest.fixture
def widget(qtbot) -> BuildWidget:
    w = BuildWidget(ProjectModel())
    qtbot.addWidget(w)
    return w


def _running_worker() -> MagicMock:
    """Worker factice qui se déclare en cours d'exécution."""
    worker = MagicMock()
    worker.isRunning.return_value = True
    return worker


class TestCancelButton:
    def test_cancel_button_exists_and_starts_disabled(self, widget):
        btn = widget.findChild(QPushButton, "btn_cancel")
        assert btn is not None
        assert btn.isEnabled() is False

    def test_is_building_false_without_worker(self, widget):
        assert widget.is_building() is False

    def test_is_building_true_while_worker_runs(self, widget):
        widget._worker = _running_worker()
        assert widget.is_building() is True

    def test_is_building_false_when_worker_finished(self, widget):
        worker = MagicMock()
        worker.isRunning.return_value = False
        widget._worker = worker
        assert widget.is_building() is False

    def test_cancel_stops_qmk_worker(self, widget):
        worker = _running_worker()
        widget._worker = worker
        widget._btn_cancel.setEnabled(True)

        widget._on_cancel_clicked()

        worker.stop.assert_called_once()
        assert widget._cancelling is True
        assert widget._btn_cancel.isEnabled() is False

    def test_cancel_stops_zmk_worker(self, widget):
        worker = _running_worker()
        widget._zmk_worker = worker
        widget._btn_cancel.setEnabled(True)

        widget._on_cancel_clicked()

        worker.stop.assert_called_once()

    def test_cancel_without_worker_is_noop(self, widget):
        widget._on_cancel_clicked()
        assert widget._cancelling is False


class TestCancelledBuildFeedback:
    """Une annulation volontaire ne doit pas remonter comme une erreur critique."""

    def test_cancelled_qmk_build_shows_no_error_dialog(self, widget):
        widget._cancelling = True
        with patch("modules.build_manager.widget.QMessageBox.critical") as crit:
            widget._on_build_error("Compilation annulée par l'utilisateur.")
        crit.assert_not_called()
        assert widget._cancelling is False
        assert widget._btn_build.isEnabled() is True

    def test_cancelled_zmk_build_shows_no_error_dialog(self, widget):
        widget._cancelling = True
        with patch("modules.build_manager.widget.QMessageBox.critical") as crit:
            widget._on_zmk_build_error("Compilation annulée par l'utilisateur.")
        crit.assert_not_called()
        assert widget._cancelling is False

    def test_real_error_still_shows_dialog(self, widget):
        with patch("modules.build_manager.widget.QMessageBox.critical") as crit:
            widget._on_build_error("undefined reference to `foo'")
        crit.assert_called_once()


class TestCleanup:
    def test_cleanup_stops_running_workers(self, widget):
        qmk, zmk = _running_worker(), _running_worker()
        widget._worker, widget._zmk_worker = qmk, zmk

        widget.cleanup()

        qmk.stop.assert_called_once()
        zmk.stop.assert_called_once()
        qmk.wait.assert_called_once()
        zmk.wait.assert_called_once()

    def test_cleanup_ignores_finished_workers(self, widget):
        worker = MagicMock()
        worker.isRunning.return_value = False
        widget._worker = worker

        widget.cleanup()

        worker.stop.assert_not_called()


class TestFirmwareType:
    """Le type de firmware pilote tout l'onglet (boutons, toolchain, export)."""

    def test_defaults_to_qmk_without_model(self, widget):
        assert widget._firmware_type() == "qmk"

    def test_qmk_for_rp2040_sofle(self, widget):
        widget._model.keyboard.model = "sofle-v2"
        widget._model.keyboard.mcu = "rp2040"
        assert widget._firmware_type() == "qmk"

    def test_zmk_for_nrf52840_mcu(self, widget):
        widget._model.keyboard.model = "sofle-v2"
        widget._model.keyboard.mcu = "nice_nano_v2"
        assert widget._firmware_type() == "zmk"

    def test_unknown_model_falls_back_to_qmk(self, widget):
        widget._model.keyboard.model = "clavier-inexistant"
        widget._model.keyboard.mcu = "nice_nano_v2"
        assert widget._firmware_type() == "qmk"


class TestRefreshForFirmware:
    def test_zmk_shows_config_button_and_hides_guide(self, widget):
        widget._model.keyboard.model = "sofle-v2"
        widget._model.keyboard.mcu = "nice_nano_v2"

        widget.refresh_for_firmware()

        assert widget._btn_zmk_config.isVisibleTo(widget) is True
        assert widget._btn_guide.isVisibleTo(widget) is False

    def test_qmk_shows_guide_and_hides_config_button(self, widget):
        widget._model.keyboard.model = "sofle-v2"
        widget._model.keyboard.mcu = "rp2040"

        widget.refresh_for_firmware()

        assert widget._btn_guide.isVisibleTo(widget) is True
        assert widget._btn_zmk_config.isVisibleTo(widget) is False

    def test_export_disabled_until_a_build_succeeded(self, widget):
        widget._model.keyboard.model = "sofle-v2"
        widget._model.keyboard.mcu = "nice_nano_v2"

        widget.refresh_for_firmware()

        assert widget._btn_export.isEnabled() is False


class TestBuildSuccess:
    def test_displays_firmware_size(self, widget, tmp_path):
        uf2 = tmp_path / "fw.uf2"
        uf2.write_bytes(b"x" * 4096)
        widget._model.keyboard.mcu = "rp2040"

        widget._on_build_success(str(uf2))

        assert "4" in widget._lbl_size.text()
        assert widget._btn_export.isEnabled() is True

    def test_warns_when_firmware_exceeds_flash(self, widget, tmp_path):
        uf2 = tmp_path / "fw.uf2"
        uf2.write_bytes(b"x" * (40 * 1024))  # > 28 KB dispo sur pro_micro
        widget._model.keyboard.mcu = "pro_micro"

        with patch("modules.build_manager.widget.QMessageBox.warning") as warn:
            widget._on_build_success(str(uf2))

        warn.assert_called_once()

    def test_no_warning_when_firmware_fits(self, widget, tmp_path):
        uf2 = tmp_path / "fw.uf2"
        uf2.write_bytes(b"x" * 1024)
        widget._model.keyboard.mcu = "rp2040"

        with patch("modules.build_manager.widget.QMessageBox.warning") as warn:
            widget._on_build_success(str(uf2))

        warn.assert_not_called()


class TestExport:
    def test_missing_source_file_disables_export(self, widget, tmp_path):
        widget._last_uf2 = str(tmp_path / "disparu.uf2")
        widget._btn_export.setEnabled(True)

        with patch("modules.build_manager.widget.QMessageBox.warning") as warn:
            widget._on_export_clicked()

        warn.assert_called_once()
        assert widget._btn_export.isEnabled() is False
        assert widget._last_uf2 is None

    def test_copies_firmware_to_chosen_path(self, widget, tmp_path):
        src = tmp_path / "fw.uf2"
        src.write_bytes(b"firmware")
        dest = tmp_path / "export" / "KFM.uf2"
        dest.parent.mkdir()
        widget._last_uf2 = str(src)

        with patch("modules.build_manager.widget.QFileDialog.getSaveFileName",
                   return_value=(str(dest), "")), \
             patch("modules.build_manager.widget.QMessageBox.information"):
            widget._on_export_clicked()

        assert dest.read_bytes() == b"firmware"

    def test_cancelled_dialog_copies_nothing(self, widget, tmp_path):
        src = tmp_path / "fw.uf2"
        src.write_bytes(b"firmware")
        widget._last_uf2 = str(src)

        with patch("modules.build_manager.widget.QFileDialog.getSaveFileName",
                   return_value=("", "")), \
             patch("modules.build_manager.widget.QMessageBox.information") as info:
            widget._on_export_clicked()

        info.assert_not_called()

    def test_zmk_export_writes_one_file_per_half(self, widget, tmp_path):
        """Les deux moitiés produisent `zmk.uf2` : le nom du build_dir les distingue."""
        widget._model.keyboard.model = "sofle-v2"
        widget._model.keyboard.mcu = "nice_nano_v2"
        uf2s = []
        for half in ("sofle_v2_left", "sofle_v2_right"):
            d = tmp_path / "build" / half / "zephyr"
            d.mkdir(parents=True)
            (d / "zmk.uf2").write_bytes(half.encode())
            uf2s.append(d / "zmk.uf2")
        widget._last_zmk_uf2s = uf2s
        out = tmp_path / "out"
        out.mkdir()

        with patch("modules.build_manager.widget.QFileDialog.getExistingDirectory",
                   return_value=str(out)), \
             patch("modules.build_manager.widget.QMessageBox.information"):
            widget._on_export_clicked()

        exported = sorted(p.name for p in out.glob("*.uf2"))
        assert exported == ["KFM_sofle-v2_sofle_v2_left.uf2", "KFM_sofle-v2_sofle_v2_right.uf2"]
