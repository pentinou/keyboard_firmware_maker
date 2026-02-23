"""Tests pour modules/build_manager/toolchain.py et vial_qmk_manager.py."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

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

    def test_ready_when_makefile_exists(self, tmp_path, monkeypatch):
        vqmk_dir = tmp_path / "vial-qmk"
        vqmk_dir.mkdir()
        (vqmk_dir / "Makefile").touch()
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", vqmk_dir)
        assert vqm.VialQmkManager().is_ready()


class TestVialQmkManagerDownload:
    def _make_fake_zip(self, zip_path: Path, sha: str) -> None:
        """Crée un zip factice imitant l'archive GitHub."""
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(f"vial-qmk-{sha}/Makefile", "# fake Makefile")
            zf.writestr(f"vial-qmk-{sha}/README.md", "# Vial-QMK")

    def test_download_creates_vial_qmk_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", tmp_path / "vial-qmk")

        def fake_urlretrieve(url, path, reporthook=None):
            self._make_fake_zip(Path(path), vqm.VIAL_QMK_SHA)

        monkeypatch.setattr(vqm.urllib.request, "urlretrieve", fake_urlretrieve)
        vqm.VialQmkManager().download()
        assert (tmp_path / "vial-qmk" / "Makefile").is_file()

    def test_download_calls_progress_callback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", tmp_path / "vial-qmk")
        calls: list[int] = []

        def fake_urlretrieve(url, path, reporthook=None):
            self._make_fake_zip(Path(path), vqm.VIAL_QMK_SHA)
            if reporthook:
                reporthook(1, 1024, 2048)  # 50%
                reporthook(2, 1024, 2048)  # 100%

        monkeypatch.setattr(vqm.urllib.request, "urlretrieve", fake_urlretrieve)
        vqm.VialQmkManager().download(progress_callback=calls.append)
        assert 50 in calls

    def test_download_removes_zip_after_extraction(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", tmp_path / "vial-qmk")

        def fake_urlretrieve(url, path, reporthook=None):
            self._make_fake_zip(Path(path), vqm.VIAL_QMK_SHA)

        monkeypatch.setattr(vqm.urllib.request, "urlretrieve", fake_urlretrieve)
        vqm.VialQmkManager().download()
        assert not (tmp_path / "vial-qmk.zip").exists()


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


# ─────────────────────────── Tests _extract_zip / download robustness ──

class TestExtractZip:
    def test_raises_when_no_vialqmk_dir_found(self, tmp_path):
        """L2 — _extract_zip lève RuntimeError si aucun dossier vial-qmk-* dans l'archive."""
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("other-dir/file.txt", "content")
        with pytest.raises(RuntimeError, match="vial-qmk-"):
            vqm._extract_zip(zip_path, tmp_path)

    def test_zip_cleaned_up_on_extraction_failure(self, tmp_path, monkeypatch):
        """M1 — Le zip doit être supprimé même si l'extraction échoue."""
        monkeypatch.setattr(vqm, "CACHE_DIR", tmp_path)
        monkeypatch.setattr(vqm, "VIAL_QMK_DIR", tmp_path / "vial-qmk")

        def fake_urlretrieve(url, path, reporthook=None):
            with zipfile.ZipFile(Path(path), "w") as zf:
                zf.writestr("other-dir/README.md", "not vial-qmk")

        monkeypatch.setattr(vqm.urllib.request, "urlretrieve", fake_urlretrieve)
        with pytest.raises(RuntimeError):
            vqm.VialQmkManager().download()
        assert not (tmp_path / "vial-qmk.zip").exists()


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
