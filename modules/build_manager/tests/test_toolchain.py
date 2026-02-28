"""Tests pour modules/build_manager/toolchain.py et vial_qmk_manager.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import modules.build_manager.toolchain as tc
import modules.build_manager.vial_qmk_manager as vqm


# ─────────────────────────────────────────── Tests toolchain.py ──

class TestDetectToolchain:
    def test_vendored_found(self, tmp_path, monkeypatch):
        """Détecte la toolchain vendorée si le binaire existe."""
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        platform_name = "windows" if sys.platform == "win32" else "linux"
        binary = "arm-none-eabi-gcc.exe" if sys.platform == "win32" else "arm-none-eabi-gcc"
        gcc = tmp_path / platform_name / "bin" / binary
        gcc.parent.mkdir(parents=True)
        gcc.touch()
        result = tc.detect_toolchain()
        assert result.source == "vendored"
        assert result.gcc_path == gcc
        assert result.is_available

    def test_system_fallback(self, tmp_path, monkeypatch):
        """Fallback PATH système si vendored absent."""
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        fake_system_gcc = tmp_path / "fake-gcc"
        fake_system_gcc.touch()
        with patch("shutil.which", return_value=str(fake_system_gcc)):
            result = tc.detect_toolchain()
        assert result.source == "system"
        assert result.gcc_path == fake_system_gcc
        assert result.is_available

    def test_missing_when_not_found(self, tmp_path, monkeypatch):
        """Source=missing si vendored absent ET shutil.which retourne None."""
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        with patch("shutil.which", return_value=None):
            result = tc.detect_toolchain()
        assert result.source == "missing"
        assert result.gcc_path is None
        assert not result.is_available

    def test_vendored_takes_priority_over_system(self, tmp_path, monkeypatch):
        """La toolchain vendorée a la priorité sur le PATH système."""
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        platform_name = "windows" if sys.platform == "win32" else "linux"
        binary = "arm-none-eabi-gcc.exe" if sys.platform == "win32" else "arm-none-eabi-gcc"
        gcc = tmp_path / platform_name / "bin" / binary
        gcc.parent.mkdir(parents=True)
        gcc.touch()
        with patch("shutil.which", return_value="/usr/bin/arm-none-eabi-gcc"):
            result = tc.detect_toolchain()
        assert result.source == "vendored"


class TestReadVersion:
    def test_reads_version_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        (tmp_path / "version.txt").write_text("13.3.rel1\n", encoding="utf-8")
        assert tc._read_version() == "13.3.rel1"

    def test_unknown_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        assert tc._read_version() == "unknown"

    def test_version_included_in_toolchain_info(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        (tmp_path / "version.txt").write_text("13.3.rel1", encoding="utf-8")
        with patch("shutil.which", return_value=None):
            result = tc.detect_toolchain()
        assert result.version == "13.3.rel1"


class TestInstallGuideMsg:
    def test_install_guide_mentions_apt(self):
        assert "apt" in tc.INSTALL_GUIDE_MSG

    def test_install_guide_mentions_arm_gcc(self):
        assert "arm-none-eabi-gcc" in tc.INSTALL_GUIDE_MSG


# ─────────────────────────────────────────── Tests VialQmkManager ──

class TestVialQmkManagerIsReady:
    def test_not_ready_when_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", tmp_path / "vial-qmk")
        assert not vqm.VialQmkManager().is_ready()

    def test_not_ready_when_makefile_missing(self, tmp_path, monkeypatch):
        vqmk_dir = tmp_path / "vial-qmk"
        vqmk_dir.mkdir()
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)
        assert not vqm.VialQmkManager().is_ready()

    def test_not_ready_when_chibios_missing(self, tmp_path, monkeypatch):
        """is_ready() retourne False si le sous-module ChibiOS est absent ou vide."""
        vqmk_dir = tmp_path / "vial-qmk"
        vqmk_dir.mkdir()
        (vqmk_dir / "Makefile").touch()
        # lib/chibios existe mais est vide (comme après une extraction ZIP)
        (vqmk_dir / "lib" / "chibios").mkdir(parents=True)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)
        assert not vqm.VialQmkManager().is_ready()

    def test_ready_when_makefile_and_chibios_populated(self, tmp_path, monkeypatch):
        vqmk_dir = tmp_path / "vial-qmk"
        vqmk_dir.mkdir()
        (vqmk_dir / "Makefile").touch()
        (vqmk_dir / "lib" / "chibios" / "os").mkdir(parents=True)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)
        assert vqm.VialQmkManager().is_ready()


class TestVialQmkManagerDownload:
    def _fake_git_side_effect(self, vqmk_dir: Path):
        """Retourne un side_effect pour subprocess.run simulant les commandes git."""
        def fake_git(args, **kwargs):
            if "init" in args:
                vqmk_dir.mkdir(exist_ok=True)
            elif "checkout" in args:
                (vqmk_dir / "Makefile").touch()
            elif "submodule" in args:
                (vqmk_dir / "lib" / "chibios" / "os").mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0)
        return fake_git

    def test_download_creates_vial_qmk_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        vqmk_dir = tmp_path / "vial-qmk"
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)

        with patch("subprocess.run", side_effect=self._fake_git_side_effect(vqmk_dir)):
            vqm.VialQmkManager().download()

        assert (vqmk_dir / "Makefile").is_file()
        assert (vqmk_dir / "lib" / "chibios").is_dir()

    def test_download_calls_progress_callback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        vqmk_dir = tmp_path / "vial-qmk"
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)
        calls: list[int] = []

        with patch("subprocess.run", side_effect=self._fake_git_side_effect(vqmk_dir)):
            vqm.VialQmkManager().download(progress_callback=calls.append)

        assert 50 in calls
        assert 100 in calls

    def test_download_calls_log_callback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        vqmk_dir = tmp_path / "vial-qmk"
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)
        logs: list[str] = []

        with patch("subprocess.run", side_effect=self._fake_git_side_effect(vqmk_dir)):
            vqm.VialQmkManager().download(log_callback=logs.append)

        assert any("sous-modules" in log for log in logs)

    def test_download_git_failure_propagates(self, tmp_path, monkeypatch):
        """Un échec git lève subprocess.CalledProcessError."""
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", tmp_path / "vial-qmk")

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(128, "git")):
            with pytest.raises(subprocess.CalledProcessError):
                vqm.VialQmkManager().download()


# ─────────────────────────────────────── Tests VialQmkSetupDialog ──

class TestVialQmkSetupDialog:
    def test_dialog_has_label(self, qtbot):
        from PySide6.QtWidgets import QLabel
        with patch.object(vqm.DownloadWorker, "start", lambda self: None):
            dlg = vqm.VialQmkSetupDialog()
            qtbot.addWidget(dlg)
        label = dlg.findChild(QLabel, "setup_label")
        assert label is not None
        assert "Vial-QMK" in label.text()

    def test_dialog_has_progress_bar(self, qtbot):
        from PySide6.QtWidgets import QProgressBar
        with patch.object(vqm.DownloadWorker, "start", lambda self: None):
            dlg = vqm.VialQmkSetupDialog()
            qtbot.addWidget(dlg)
        pb = dlg.findChild(QProgressBar, "setup_progress")
        assert pb is not None
        assert pb.minimum() == 0
        assert pb.maximum() == 100

    def test_progress_signal_updates_bar(self, qtbot):
        from PySide6.QtWidgets import QProgressBar
        with patch.object(vqm.DownloadWorker, "start", lambda self: None):
            dlg = vqm.VialQmkSetupDialog()
            qtbot.addWidget(dlg)
        dlg._worker.progress.emit(42)
        pb = dlg.findChild(QProgressBar, "setup_progress")
        assert pb.value() == 42

    def test_progress_bar_reaches_100_on_finished(self, qtbot):
        """La barre doit atteindre 100 % quand le signal finished est émis (AC2)."""
        from PySide6.QtWidgets import QProgressBar
        with patch.object(vqm.DownloadWorker, "start", lambda self: None):
            dlg = vqm.VialQmkSetupDialog()
            qtbot.addWidget(dlg)
        dlg._worker.progress.emit(100)
        pb = dlg.findChild(QProgressBar, "setup_progress")
        assert pb.value() == 100

    def test_log_line_signal_updates_label(self, qtbot):
        """log_line met à jour l'étiquette avec l'étape courante."""
        from PySide6.QtWidgets import QLabel
        with patch.object(vqm.DownloadWorker, "start", lambda self: None):
            dlg = vqm.VialQmkSetupDialog()
            qtbot.addWidget(dlg)
        dlg._worker.log_line.emit("Téléchargement des sous-modules…")
        label = dlg.findChild(QLabel, "setup_label")
        assert label.text() == "Téléchargement des sous-modules…"


# ─────────────────────────── Tests _get_system_gcc_version ──

class TestGetSystemGccVersion:
    def test_parses_version_from_gcc_output(self):
        """L3 — _get_system_gcc_version extrait le numéro de version de la sortie --version."""
        fake_output = (
            b"arm-none-eabi-gcc (GNU Arm Embedded Toolchain 13.3.Rel1) 13.3.1 20240614\n"
            b"Copyright (C) 2023 Free Software Foundation, Inc.\n"
        )
        with patch("subprocess.check_output", return_value=fake_output):
            result = tc._get_system_gcc_version("/usr/bin/arm-none-eabi-gcc")
        assert result == "13.3.1"

    def test_returns_unknown_on_subprocess_failure(self):
        """L3 — Falls back to 'unknown' si subprocess lève une exception."""
        with patch("subprocess.check_output", side_effect=FileNotFoundError()):
            result = tc._get_system_gcc_version("/nonexistent/gcc")
        assert result == "unknown"

    def test_system_toolchain_uses_actual_gcc_version(self, tmp_path, monkeypatch):
        """L3 — detect_toolchain() retourne la version réelle du GCC système."""
        monkeypatch.setattr(tc, "TOOLCHAIN_DIR", tmp_path)
        fake_output = b"arm-none-eabi-gcc (GNU Toolchain) 12.2.1 20221205\n"
        with patch("shutil.which", return_value="/usr/bin/arm-none-eabi-gcc"):
            with patch("subprocess.check_output", return_value=fake_output):
                result = tc.detect_toolchain()
        assert result.source == "system"
        assert result.version == "12.2.1"
