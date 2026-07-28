"""Tests pour modules/hardware/vialqmk_scanner.py.

Le scanner indexe les 620+ claviers du dépôt vial-qmk et alimente le combo de
l'onglet Matériel. Les tests travaillent sur une arborescence factice ; le
fichier de cache réel de l'utilisateur est systématiquement redirigé vers
tmp_path par la fixture `isolated_cache`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.hardware import vialqmk_scanner as scanner
from modules.hardware.vialqmk_scanner import (
    CATEGORY_FULLSIZE,
    CATEGORY_SPLIT,
    VialKeyboardEntry,
    categorize_keyboard,
    count_keys_from_keymap,
    load_vial_keyboard,
    scan_vial_keyboards,
)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Ne jamais écrire dans ~/.keyboard_firmware_maker/vial-qmk-index.json."""
    monkeypatch.setattr(scanner, "CACHE_FILE", tmp_path / "index.json")


def _make_keyboard(
    root: Path,
    qmk_path: str,
    *,
    keymap_dir: str = "vial",
    keyboard_json: dict | None = None,
    vial_json: dict | None = None,
) -> Path:
    """Crée keyboards/<qmk_path>/ avec son keyboard.json et son vial.json."""
    kb_dir = root / "keyboards" / qmk_path
    (kb_dir / "keymaps" / keymap_dir).mkdir(parents=True)
    if keyboard_json is not None:
        (kb_dir / "keyboard.json").write_text(json.dumps(keyboard_json), encoding="utf-8")
    payload = vial_json if vial_json is not None else {"layouts": {"keymap": [["A", "B"], ["C", "D"]]}}
    (kb_dir / "keymaps" / keymap_dir / "vial.json").write_text(json.dumps(payload), encoding="utf-8")
    return kb_dir


class TestCategorizeKeyboard:
    def test_split_wins_over_key_count(self):
        assert categorize_keyboard(58, is_split=True) == CATEGORY_SPLIT
        assert categorize_keyboard(4, is_split=True) == CATEGORY_SPLIT

    @pytest.mark.parametrize(
        ("keys", "expected"),
        [(4, "macropad"), (30, "macropad"), (31, "40pct"), (50, "40pct"),
         (51, "60pct"), (68, "60pct"), (69, "75pct"), (80, "75pct"),
         (81, "tkl"), (90, "tkl")],
    )
    def test_thresholds(self, keys, expected):
        assert categorize_keyboard(keys, is_split=False) == expected

    def test_above_last_threshold_is_fullsize(self):
        assert categorize_keyboard(104, is_split=False) == CATEGORY_FULLSIZE


class TestCountKeysFromKeymap:
    def test_counts_strings_only(self):
        # Les dicts KLE portent les métadonnées de position, pas des touches
        keymap = [[{"y": 0.5}, "0,0", "0,1"], [{"x": 1}, "1,0"]]
        assert count_keys_from_keymap(keymap) == 3

    def test_ignores_non_list_rows(self):
        assert count_keys_from_keymap(["pas une rangée", ["0,0"]]) == 1

    def test_empty_keymap(self):
        assert count_keys_from_keymap([]) == 0


class TestSearchText:
    def test_combines_name_and_path_lowercased(self):
        entry = VialKeyboardEntry(
            name="Sofle RGB", qmk_path="foostan/Sofle",
            keyboard_dir=Path("/x"), vial_json_path=Path("/x/vial.json"),
        )
        assert entry.search_text == "sofle rgb foostan/sofle"


class TestScan:
    def test_returns_empty_when_keyboards_dir_missing(self, tmp_path):
        assert scan_vial_keyboards(tmp_path / "vide") == []

    def test_indexes_keyboard_with_vial_json(self, tmp_path):
        _make_keyboard(tmp_path, "crkbd", keyboard_json={"keyboard_name": "Corne", "processor": "RP2040"})

        entries = scan_vial_keyboards(tmp_path)

        assert len(entries) == 1
        assert entries[0].name == "Corne"
        assert entries[0].processor == "RP2040"
        assert entries[0].qmk_path == "crkbd"

    def test_accepts_default_keymap_directory(self, tmp_path):
        _make_keyboard(tmp_path, "planck", keymap_dir="default")

        entries = scan_vial_keyboards(tmp_path)

        assert len(entries) == 1
        assert entries[0].vial_json_path.parent.name == "default"

    def test_ignores_vial_json_outside_keymaps(self, tmp_path):
        stray = tmp_path / "keyboards" / "orphan" / "docs"
        stray.mkdir(parents=True)
        (stray / "vial.json").write_text("{}", encoding="utf-8")

        assert scan_vial_keyboards(tmp_path) == []

    def test_falls_back_to_path_as_name(self, tmp_path):
        _make_keyboard(tmp_path, "vendor/board")

        entries = scan_vial_keyboards(tmp_path)

        assert entries[0].name == "Vendor / Board"

    def test_detects_split_and_categorises(self, tmp_path):
        _make_keyboard(
            tmp_path, "sofle",
            keyboard_json={"keyboard_name": "Sofle", "split": {"enabled": True}},
        )

        entries = scan_vial_keyboards(tmp_path)

        assert entries[0].is_split is True
        assert entries[0].category == CATEGORY_SPLIT

    def test_counts_keys_from_vial_json(self, tmp_path):
        _make_keyboard(
            tmp_path, "macro",
            vial_json={"layouts": {"keymap": [["0,0", "0,1"], ["1,0"]]}},
        )

        assert scan_vial_keyboards(tmp_path)[0].key_count == 3

    def test_survives_malformed_vial_json(self, tmp_path):
        kb = _make_keyboard(tmp_path, "broken")
        (kb / "keymaps" / "vial" / "vial.json").write_text("{ pas du json", encoding="utf-8")

        entries = scan_vial_keyboards(tmp_path)

        assert len(entries) == 1
        assert entries[0].key_count == 0

    def test_entries_sorted_by_name(self, tmp_path):
        _make_keyboard(tmp_path, "zeta", keyboard_json={"keyboard_name": "Zeta"})
        _make_keyboard(tmp_path, "alpha", keyboard_json={"keyboard_name": "alpha"})

        names = [e.name for e in scan_vial_keyboards(tmp_path)]

        assert names == ["alpha", "Zeta"]

    def test_merges_revision_over_parent(self, tmp_path):
        """QMK fusionne hiérarchiquement : la révision surcharge le parent."""
        kb = _make_keyboard(
            tmp_path, "board",
            keyboard_json={"keyboard_name": "Board", "processor": "atmega32u4"},
        )
        rev = kb / "rev2"
        rev.mkdir()
        (rev / "keyboard.json").write_text(json.dumps({"processor": "RP2040"}), encoding="utf-8")

        assert scan_vial_keyboards(tmp_path)[0].processor == "RP2040"


class TestCache:
    def test_index_is_cached_and_reused(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scanner, "_get_git_sha", lambda _d: "sha-1234")
        _make_keyboard(tmp_path, "crkbd", keyboard_json={"keyboard_name": "Corne"})

        first = scan_vial_keyboards(tmp_path)
        assert scanner.CACHE_FILE.is_file()

        # Le clavier disparaît du disque : seul le cache peut encore le fournir
        import shutil
        shutil.rmtree(tmp_path / "keyboards" / "crkbd")
        second = scan_vial_keyboards(tmp_path)

        assert [e.name for e in second] == [e.name for e in first]

    def test_cache_invalidated_by_new_sha(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scanner, "_get_git_sha", lambda _d: "sha-old")
        _make_keyboard(tmp_path, "crkbd", keyboard_json={"keyboard_name": "Corne"})
        scan_vial_keyboards(tmp_path)

        _make_keyboard(tmp_path, "planck", keyboard_json={"keyboard_name": "Planck"})
        monkeypatch.setattr(scanner, "_get_git_sha", lambda _d: "sha-new")

        assert len(scan_vial_keyboards(tmp_path)) == 2

    def test_corrupted_cache_triggers_rescan(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scanner, "_get_git_sha", lambda _d: "sha-1234")
        _make_keyboard(tmp_path, "crkbd", keyboard_json={"keyboard_name": "Corne"})
        scanner.CACHE_FILE.write_text("{{{ corrompu", encoding="utf-8")

        assert len(scan_vial_keyboards(tmp_path)) == 1

    def test_no_cache_written_without_git_sha(self, tmp_path, monkeypatch):
        """Hors dépôt git, l'index ne peut pas être invalidé : on ne le persiste pas."""
        monkeypatch.setattr(scanner, "_get_git_sha", lambda _d: "")
        _make_keyboard(tmp_path, "crkbd")

        scan_vial_keyboards(tmp_path)

        assert not scanner.CACHE_FILE.exists()


class TestLoadVialKeyboard:
    def test_builds_definition_with_hardware_details(self, tmp_path):
        _make_keyboard(
            tmp_path, "sofle",
            keyboard_json={
                "keyboard_name": "Sofle",
                "processor": "RP2040",
                "bootloader": "rp2040",
                "diode_direction": "COL2ROW",
                "features": {"oled": True, "rgb_matrix": True, "encoder": True},
                "matrix_pins": {"rows": ["GP1", "GP2"], "cols": ["GP3", "GP4", "GP5"]},
                "split": {"enabled": True, "serial": {"pin": "GP0"}},
                "ws2812": {"pin": "GP6"},
                "encoder": {"rotary": [{"pin_a": "GP7", "pin_b": "GP8"}]},
            },
        )
        entry = scan_vial_keyboards(tmp_path)[0]

        kb = load_vial_keyboard(entry)

        assert kb.split is True
        assert kb.has_encoder is True
        assert kb.capabilities == {"oled": True, "rgb": True}
        assert kb.mcu_options[0].id == "rp2040"
        assert kb.mcu_options[0].pins.serial_tx == "GP0"
        assert kb.mcu_options[0].pins.ws2812 == "GP6"
        assert kb.mcu_options[0].pins.encoder_a == ["GP7"]
        assert kb.matrix == {"rows": 4, "cols": 3}  # 2 rangées × 2 moitiés
        assert kb.vial_qmk_keyboard == "sofle"

    def test_model_slug_replaces_slashes(self, tmp_path):
        _make_keyboard(tmp_path, "vendor/board")

        kb = load_vial_keyboard(scan_vial_keyboards(tmp_path)[0])

        assert kb.model == "vendor-board"

    def test_rgblight_alone_enables_rgb(self, tmp_path):
        _make_keyboard(tmp_path, "board", keyboard_json={"features": {"rgblight": True}})

        kb = load_vial_keyboard(scan_vial_keyboards(tmp_path)[0])

        assert kb.capabilities["rgb"] is True

    def test_matrix_falls_back_to_vial_json(self, tmp_path):
        """Sans matrix_pins, la taille de matrice vient du vial.json."""
        _make_keyboard(
            tmp_path, "board",
            keyboard_json={"keyboard_name": "Board"},
            vial_json={"matrix": {"rows": 5, "cols": 14}, "layouts": {"keymap": [["0,0"]]}},
        )

        kb = load_vial_keyboard(scan_vial_keyboards(tmp_path)[0])

        assert kb.matrix == {"rows": 5, "cols": 14}

    def test_split_layout_is_divided_left_right(self, tmp_path):
        """Les touches sont réparties par position x autour du milieu du clavier."""
        keymap = [["0,0", "0,1", {"x": 4}, "0,2", "0,3"]]
        _make_keyboard(
            tmp_path, "split_board",
            keyboard_json={"split": {"enabled": True}},
            vial_json={"layouts": {"keymap": keymap}},
        )

        kb = load_vial_keyboard(scan_vial_keyboards(tmp_path)[0])

        assert len(kb.layout["left"]) == 2
        assert len(kb.layout["right"]) == 2
        assert kb.layout["keys"] == []

    def test_non_split_layout_goes_to_keys(self, tmp_path):
        _make_keyboard(tmp_path, "mono", vial_json={"layouts": {"keymap": [["0,0", "0,1"]]}})

        kb = load_vial_keyboard(scan_vial_keyboards(tmp_path)[0])

        assert len(kb.layout["keys"]) == 2
        assert kb.layout["left"] == []
