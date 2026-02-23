"""Tests pour modules/project_manager/file_io.py — save_project et load_project."""
from __future__ import annotations

import json

import pytest

from models.project_model import ProjectModel
from modules.project_manager.file_io import load_project, save_project


def test_save_project_creates_file(tmp_path):
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    assert path.exists()


def test_save_project_valid_json(tmp_path):
    model = ProjectModel()
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    data = json.loads(path.read_text())
    assert "keyboard" in data
    assert "version" in data


def test_save_project_snake_case_keys(tmp_path):
    model = ProjectModel()
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    data = json.loads(path.read_text())
    assert "keyboard" in data          # snake_case
    assert "image_path" in data["oled"]  # snake_case


def test_save_project_no_tmp_file_remains(tmp_path):
    """M2 fix — le fichier tmp est test.kfm.tmp (with_suffix remplace .json), pas test.tmp."""
    model = ProjectModel()
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    assert not (tmp_path / "test.kfm.tmp").exists()


def test_load_project_roundtrip(tmp_path):
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.keyboard.mcu = "rp2040"
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    loaded = load_project(path)
    assert loaded.keyboard.model == "sofle-v2"
    assert loaded.keyboard.mcu == "rp2040"


def test_load_project_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        load_project(tmp_path / "nonexistent.kfm.json")


def test_load_project_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.kfm.json"
    path.write_text("not json {{{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_project(path)


def test_save_project_frames_not_serialized(tmp_path):
    """Les frames OLED ne doivent pas apparaître dans le JSON (Story 1.1)."""
    model = ProjectModel()
    model.oled.frames = [b'\x00\xFF']  # données runtime
    path = tmp_path / "test.kfm.json"
    save_project(model, path)
    data = json.loads(path.read_text())
    assert "frames" not in data.get("oled", {})


def test_save_project_overwrites_existing(tmp_path):
    """Sauvegarder deux fois écrase l'ancienne version."""
    path = tmp_path / "test.kfm.json"
    model = ProjectModel()
    model.keyboard.model = "corne"
    save_project(model, path)

    model.keyboard.model = "sofle-v2"
    save_project(model, path)

    loaded = load_project(path)
    assert loaded.keyboard.model == "sofle-v2"


def test_no_qt_import_in_file_io():
    """file_io.py ne doit contenir aucun import PySide6/PyQt (testable sans QApplication)."""
    from pathlib import Path
    source = Path(__file__).parent.parent / "file_io.py"
    content = source.read_text(encoding="utf-8")
    assert "PySide6" not in content
    assert "PyQt" not in content
