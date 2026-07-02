"""Tests pour uf2_validator.py, builder.py et widget.py."""
from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models.project_model import ProjectModel
from modules.build_manager.uf2_validator import (
    UF2_BLOCK_SIZE,
    UF2_MAGIC_START0,
    UF2_MAGIC_START1,
    validate_uf2,
)


def _make_valid_uf2_block() -> bytes:
    """Crée un bloc UF2 valide de 512 octets."""
    block = bytearray(UF2_BLOCK_SIZE)
    struct.pack_into("<II", block, 0, UF2_MAGIC_START0, UF2_MAGIC_START1)
    return bytes(block)


# ─────────────────────────────────────────── Tests uf2_validator ──

class TestValidateUf2:
    def test_valid_single_block(self, tmp_path):
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(_make_valid_uf2_block())
        result = validate_uf2(uf2)
        assert result.valid
        assert result.size_bytes == UF2_BLOCK_SIZE

    def test_valid_multiple_blocks(self, tmp_path):
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(_make_valid_uf2_block() * 4)
        result = validate_uf2(uf2)
        assert result.valid
        assert result.size_bytes == UF2_BLOCK_SIZE * 4

    def test_invalid_file_not_found(self, tmp_path):
        result = validate_uf2(tmp_path / "nonexistent.uf2")
        assert not result.valid
        assert result.size_bytes == 0

    def test_invalid_too_small(self, tmp_path):
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(b"\x00" * 100)
        result = validate_uf2(uf2)
        assert not result.valid
        assert "trop petit" in result.message

    def test_invalid_size_not_multiple_of_512(self, tmp_path):
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(b"\x00" * (UF2_BLOCK_SIZE + 100))
        result = validate_uf2(uf2)
        assert not result.valid
        assert "multiple de 512" in result.message

    def test_invalid_wrong_magic0(self, tmp_path):
        block = bytearray(_make_valid_uf2_block())
        struct.pack_into("<I", block, 0, 0xDEADBEEF)
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(bytes(block))
        result = validate_uf2(uf2)
        assert not result.valid
        assert "Magic" in result.message

    def test_invalid_wrong_magic1(self, tmp_path):
        block = bytearray(_make_valid_uf2_block())
        struct.pack_into("<I", block, 4, 0xDEADBEEF)
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(bytes(block))
        result = validate_uf2(uf2)
        assert not result.valid

    def test_valid_message_contains_size_info(self, tmp_path):
        uf2 = tmp_path / "test.uf2"
        uf2.write_bytes(_make_valid_uf2_block() * 2048)  # 1 MB
        result = validate_uf2(uf2)
        assert result.valid
        assert "1024 KB" in result.message or "blocs" in result.message


# ─────────────────────────────────────────── Tests BuildWorker ──

class TestBuildWorker:
    def _model(self):
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "rp2040"
        return m

    def test_worker_emits_error_if_make_missing(self, qtbot, tmp_path):
        """Si 'make' est absent, error signal émis."""
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        errors: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.return_value = {}

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.error.connect(errors.append)

        with patch("subprocess.Popen", side_effect=FileNotFoundError("make not found")):
            worker.run()

        assert len(errors) == 1
        assert "make" in errors[0].lower() or "introuvable" in errors[0].lower()

    def test_worker_emits_error_if_make_fails(self, qtbot, tmp_path):
        """Si make retourne code != 0, error signal émis."""
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        errors: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.return_value = {}

        mock_proc = MagicMock()
        mock_proc.stdout = iter(["[  10%] Building...\n", "error: something failed\n"])
        mock_proc.returncode = 1
        mock_proc.wait.return_value = None

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.error.connect(errors.append)

        with patch("subprocess.Popen", return_value=mock_proc):
            worker.run()

        assert len(errors) == 1
        assert "échoué" in errors[0].lower() or "compilation" in errors[0].lower()

    def test_worker_emits_progress_from_make_output(self, qtbot, tmp_path):
        """Les lignes [  X%] doivent émettre des signaux progress."""
        from modules.build_manager.builder import BuildWorker, _parse_progress
        from modules.build_manager.template_generator import TemplateGenerator

        progress_vals: list[int] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.return_value = {}

        mock_proc = MagicMock()
        mock_proc.stdout = iter(["[  10%] Building foo.c\n", "[  50%] Linking\n"])
        mock_proc.returncode = 1  # fail but we still check progress
        mock_proc.wait.return_value = None

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.progress.connect(progress_vals.append)
        worker.error.connect(lambda _: None)

        with patch("subprocess.Popen", return_value=mock_proc):
            worker.run()

        # Should have received progress from [10%] and [50%]
        assert any(v > 10 for v in progress_vals)

    def test_parse_progress_extracts_percent(self):
        from modules.build_manager.builder import _parse_progress
        assert _parse_progress("[  1%] Building...") == 1
        assert _parse_progress("[ 50%] Linking...") == 50
        assert _parse_progress("[100%] Done") == 100
        assert _parse_progress("regular log line") is None

    def test_worker_emits_success_with_valid_uf2(self, qtbot, tmp_path):
        """Si le build réussit et trouve un .uf2 valide, success signal émis."""
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        # Create a fake valid .uf2 file là où make l'écrit (.build/)
        (tmp_path / ".build").mkdir()
        uf2_path = tmp_path / ".build" / "keyboard_firmware_maker_default.uf2"
        uf2_path.write_bytes(_make_valid_uf2_block() * 2)

        successes: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.return_value = {}

        mock_proc = MagicMock()
        mock_proc.stdout = iter(["[100%] Done\n"])
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.success.connect(successes.append)
        worker.error.connect(lambda _: None)

        with patch("subprocess.Popen", return_value=mock_proc):
            worker.run()

        assert len(successes) == 1
        assert successes[0].endswith(".uf2")

    def test_stale_uf2_outside_build_dir_not_picked(self, qtbot, tmp_path):
        """Un .uf2 périmé ailleurs dans vial-qmk ne doit pas être pris pour
        le résultat du build (régression : ancien rglob global par mtime)."""
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        # Artefact périmé à la racine (ex: copie d'un build précédent)
        stale = tmp_path / "old_other_keyboard.uf2"
        stale.write_bytes(_make_valid_uf2_block() * 2)

        errors: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.return_value = {}

        mock_proc = MagicMock()
        mock_proc.stdout = iter(["[100%] Done\n"])
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.error.connect(errors.append)
        worker.success.connect(lambda _: None)

        with patch("subprocess.Popen", return_value=mock_proc):
            worker.run()

        # Pas de .uf2 dans .build/ → erreur "introuvable", pas le stale
        assert len(errors) == 1
        assert "introuvable" in errors[0].lower()

    def test_stop_kills_active_process(self, tmp_path):
        """stop() doit tuer le sous-processus make en cours (parité ZmkBuildWorker)."""
        from modules.build_manager.builder import BuildWorker

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
        )
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        worker._proc = mock_proc
        worker.stop()
        mock_proc.kill.assert_called_once()

    def test_stop_skips_kill_if_no_process(self, tmp_path):
        from modules.build_manager.builder import BuildWorker

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
        )
        worker.stop()  # ne doit pas lever


# ─────────────────────────────────────────── Tests BuildWidget ──

class TestBuildWidget:
    @pytest.fixture
    def widget(self, qtbot):
        from modules.build_manager.widget import BuildWidget
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "rp2040"
        w = BuildWidget(m)
        qtbot.addWidget(w)
        return w

    def test_build_button_exists(self, widget):
        from PySide6.QtWidgets import QPushButton
        btn = widget.findChild(QPushButton, "btn_build")
        assert btn is not None

    def test_progress_bar_exists(self, widget):
        from PySide6.QtWidgets import QProgressBar
        pb = widget.findChild(QProgressBar, "build_progress")
        assert pb is not None
        assert pb.minimum() == 0
        assert pb.maximum() == 100

    def test_log_widget_exists(self, widget):
        from PySide6.QtWidgets import QPlainTextEdit
        log = widget.findChild(QPlainTextEdit, "build_log")
        assert log is not None
        assert log.isReadOnly()

    def test_toolchain_label_exists(self, widget):
        from PySide6.QtWidgets import QLabel
        lbl = widget.findChild(QLabel, "lbl_toolchain")
        assert lbl is not None

    def test_size_label_exists(self, widget):
        from PySide6.QtWidgets import QLabel
        lbl = widget.findChild(QLabel, "lbl_firmware_size")
        assert lbl is not None

    def test_build_click_shows_warning_if_toolchain_missing(self, widget, qtbot):
        from unittest.mock import patch
        from modules.build_manager.toolchain import ToolchainInfo
        missing = ToolchainInfo(gcc_path=None, version="unknown", source="missing")
        with patch("modules.build_manager.widget.detect_toolchain", return_value=missing):
            with patch("modules.build_manager.widget.QMessageBox.warning") as mock_warn:
                widget._on_build_clicked()
        mock_warn.assert_called_once()

    def test_build_click_shows_warning_if_vial_qmk_not_ready(self, widget, qtbot):
        from pathlib import Path
        from unittest.mock import patch
        from modules.build_manager.toolchain import ToolchainInfo
        available = ToolchainInfo(gcc_path=Path("/fake/gcc"), version="13.3.rel1", source="system")
        with patch("modules.build_manager.widget.detect_toolchain", return_value=available):
            with patch("modules.build_manager.widget.VialQmkManager.is_ready", return_value=False):
                with patch("modules.build_manager.widget.QMessageBox.warning") as mock_warn:
                    widget._on_build_clicked()
        mock_warn.assert_called_once()
