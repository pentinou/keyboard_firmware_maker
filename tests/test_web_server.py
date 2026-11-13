"""Interface web : fonctions du serveur (sans HTTP ni compilation)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from models.project_model import CustomEffect, EffectStep, EffectTrack, OledImageItem, ProjectModel
from web import jobs, server


def test_full_project_round_trip():
    """Le projet complet envoyé au navigateur redonne exactement le même modèle."""
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.rgb.custom_effects.append(CustomEffect(name="vague", tracks=[
        EffectTrack(target_mode="fixed", keys_fixed=["L_r3_c0"], trigger_keys=["R_r4_c4"],
                    steps=[EffectStep(time_ms=100, color="#FFFFFF", hold_ms=100)]),
    ]))
    model.oled.left.images.append(OledImageItem(image_path="/x.png", frames=[b"\x00"], delays=[100]))

    data = server.full_project(model)

    json.dumps(data)  # sérialisable : les frames binaires sont retirées
    assert "frames" not in data["oled"]["left"]["images"][0]
    # les listes vides que to_dict() omet sont présentes (l'interface les lit)
    assert data["rgb"]["enabled_effects"] == []
    assert data["rgb"]["custom_effects"][0]["tracks"][0]["keys_offset"] == []
    assert ProjectModel.from_dict(data).to_dict() == model.to_dict()


def test_firmware_of_rejects_unknown_or_traversal():
    model = ProjectModel()
    model.keyboard.model = "sofle-v2"
    model.keyboard.mcu = "nice_nano_v2"
    assert jobs.firmware_of(model) == "zmk"
    model.keyboard.mcu = "rp2040"
    assert jobs.firmware_of(model) == "qmk"

    model.keyboard.mcu = "inconnu"
    with pytest.raises(ValueError):
        jobs.firmware_of(model)
    model.keyboard.model = "../keyboards/sofle-v2"
    with pytest.raises(ValueError):
        jobs.firmware_of(model)


def test_image_info_refuses_files_outside_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS_DIR", tmp_path / "uploads")
    outside = tmp_path / "secret.png"
    Image.new("L", (8, 8), 255).save(outside)
    with pytest.raises(FileNotFoundError):
        server.image_info(str(outside))


def test_save_image_then_preview(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "UPLOADS_DIR", tmp_path / "uploads")
    src = tmp_path / "logo.png"
    Image.new("L", (64, 64), 255).save(src)

    info = server.save_image("../../logo.png", src.read_bytes())

    assert (tmp_path / "uploads") in Path(info["image_path"]).parents
    assert (info["natural_w"], info["natural_h"]) == (32, 32)
    assert info["preview"].startswith("data:image/png;base64,")
    with pytest.raises(ValueError):
        server.save_image("script.sh", b"#!/bin/sh")


def test_load_image_frames_ignores_paths_outside_uploads(tmp_path, monkeypatch):
    """Un projet ne doit pas faire lire au serveur un fichier arbitraire."""
    monkeypatch.setattr(jobs, "UPLOADS_DIR", tmp_path / "uploads")
    outside = tmp_path / "ailleurs.png"
    Image.new("L", (8, 8), 255).save(outside)
    model = ProjectModel()
    model.oled.left.images.append(OledImageItem(image_path=str(outside)))
    logs: list[str] = []

    jobs.load_image_frames(model, logs.append)

    assert model.oled.left.images[0].frames == []
    assert logs and "ignorée" in logs[0]


def test_import_keymap_vial_and_unknown():
    vial = json.dumps({"layout": [[["KC_A"]]]})
    r = server.import_keymap("penti.vil", vial, "qmk")
    assert r["format"] == "vial" and not r["cross_format"]
    assert server.import_keymap("penti.vil", vial, "zmk")["cross_format"]
    with pytest.raises(ValueError):
        server.import_keymap("x.txt", "bonjour", "qmk")
