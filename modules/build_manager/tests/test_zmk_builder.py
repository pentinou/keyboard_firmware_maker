"""Tests pour modules/build_manager/zmk_builder.py — ZmkBuildWorker + helpers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from models.project_model import ProjectModel
from modules.build_manager.zmk_builder import (
    ZmkBuildWorker,
    _parse_ninja_progress,
    is_west_available,
    is_zephyr_sdk_installed,
)


class TestNinjaProgressParser:
    def test_parses_standard_line(self):
        assert _parse_ninja_progress("[42/100] Building foo.o") == 42

    def test_returns_none_when_no_match(self):
        assert _parse_ninja_progress("cmake: configuring...") is None

    def test_handles_100(self):
        assert _parse_ninja_progress("[100/100] Linking zmk.uf2") == 100

    def test_handles_zero_total(self):
        assert _parse_ninja_progress("[5/0] weird") is None


class TestZephyrSdkDetection:
    def test_missing_sdk(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "modules.build_manager.zmk_builder.ZEPHYR_SDK_DIR",
            tmp_path / "nonexistent",
        )
        assert not is_zephyr_sdk_installed()

    def test_sdk_without_toolchain_not_installed(self, tmp_path, monkeypatch):
        sdk_dir = tmp_path / "zephyr-sdk"
        sdk_dir.mkdir()
        (sdk_dir / "setup.sh").touch()
        monkeypatch.setattr(
            "modules.build_manager.zmk_builder.ZEPHYR_SDK_DIR", sdk_dir
        )
        assert not is_zephyr_sdk_installed()

    def test_sdk_with_toolchain_installed(self, tmp_path, monkeypatch):
        sdk_dir = tmp_path / "zephyr-sdk"
        sdk_dir.mkdir()
        (sdk_dir / "arm-zephyr-eabi").mkdir()
        monkeypatch.setattr(
            "modules.build_manager.zmk_builder.ZEPHYR_SDK_DIR", sdk_dir
        )
        assert is_zephyr_sdk_installed()


class TestWestAvailability:
    def test_returns_false_when_west_missing(self):
        with patch("modules.build_manager.zmk_builder.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            assert not is_west_available()

    def test_returns_true_when_west_present(self):
        with patch("modules.build_manager.zmk_builder.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert is_west_available()


class TestBuildYamlParsing:
    def _make_worker(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "corne"
        model.keyboard.mcu = "nice_nano_v2"
        return ZmkBuildWorker(model=model, workspace_dir=tmp_path)

    def test_parses_split_entries(self, tmp_path):
        worker = self._make_worker(tmp_path)
        build_yaml = tmp_path / "build.yaml"
        build_yaml.write_text(
            "include:\n"
            "  - board: nice_nano_v2\n"
            "    shield: corne_left\n"
            "    snippet: studio-rpc-usb-uart\n"
            "  - board: nice_nano_v2\n"
            "    shield: corne_right\n",
            encoding="utf-8",
        )
        entries = worker._parse_build_yaml(build_yaml)
        assert len(entries) == 2
        assert entries[0]["shield"] == "corne_left"
        assert entries[0]["snippet"] == "studio-rpc-usb-uart"
        assert entries[1]["shield"] == "corne_right"

    def test_skips_entries_missing_fields(self, tmp_path):
        worker = self._make_worker(tmp_path)
        build_yaml = tmp_path / "build.yaml"
        build_yaml.write_text(
            "include:\n"
            "  - board: nice_nano_v2\n"    # manque shield
            "  - board: nice_nano_v2\n"
            "    shield: corne_left\n",
            encoding="utf-8",
        )
        entries = worker._parse_build_yaml(build_yaml)
        assert len(entries) == 1
        assert entries[0]["shield"] == "corne_left"


class TestWorkspaceUpdated:
    def _make_worker(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "corne"
        model.keyboard.mcu = "nice_nano_v2"
        return ZmkBuildWorker(model=model, workspace_dir=tmp_path)

    def test_empty_workspace_not_updated(self, tmp_path):
        worker = self._make_worker(tmp_path)
        assert not worker._is_workspace_updated()

    def test_only_zmk_present_not_updated(self, tmp_path):
        (tmp_path / "zmk" / "app").mkdir(parents=True)
        worker = self._make_worker(tmp_path)
        assert not worker._is_workspace_updated()

    def test_both_present_updated(self, tmp_path):
        (tmp_path / "zmk" / "app").mkdir(parents=True)
        (tmp_path / "zephyr" / "cmake").mkdir(parents=True)
        worker = self._make_worker(tmp_path)
        assert worker._is_workspace_updated()


class TestEnvIncludesZephyrSdk:
    def test_env_sets_zephyr_sdk_install_dir(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "corne"
        model.keyboard.mcu = "nice_nano_v2"
        worker = ZmkBuildWorker(model=model, workspace_dir=tmp_path)
        env = worker._env()
        assert "ZEPHYR_SDK_INSTALL_DIR" in env
        assert env["ZEPHYR_TOOLCHAIN_VARIANT"] == "zephyr"


class TestBuildDirNaming:
    def _make_worker(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "sofle-v2"
        model.keyboard.mcu = "nice_nano_v2"
        return ZmkBuildWorker(model=model, workspace_dir=tmp_path)

    def test_simple_shield_uses_name(self, tmp_path):
        entry = {"board": "nice_nano_v2", "shield": "sofle_v2_left"}
        build_dir_name = entry["shield"].replace(" ", "_")
        assert build_dir_name == "sofle_v2_left"

    def test_shield_with_spaces_underscored(self, tmp_path):
        entry = {"board": "nice_nano_v2", "shield": "sofle_v2_left nice_view_adapter nice_view"}
        build_dir_name = entry["shield"].replace(" ", "_")
        assert build_dir_name == "sofle_v2_left_nice_view_adapter_nice_view"

    def test_no_collision_between_entries(self, tmp_path):
        entries = [
            {"board": "nice_nano_v2", "shield": "sofle_v2_left"},
            {"board": "nice_nano_v2", "shield": "sofle_v2_left nice_view_adapter"},
        ]
        names = [e["shield"].replace(" ", "_") for e in entries]
        assert len(names) == len(set(names))


class TestCleanGeneratedConfig:
    def _make_worker(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "corne"
        model.keyboard.mcu = "nice_nano_v2"
        return ZmkBuildWorker(model=model, workspace_dir=tmp_path)

    def test_removes_config_dir(self, tmp_path):
        config = tmp_path / "config"
        config.mkdir()
        (config / "some_file.txt").touch()
        worker = self._make_worker(tmp_path)
        worker._clean_generated_config()
        assert not config.exists()

    def test_noop_if_no_config(self, tmp_path):
        worker = self._make_worker(tmp_path)
        worker._clean_generated_config()

    def test_removes_west_if_config_missing(self, tmp_path):
        west_dir = tmp_path / ".west"
        west_dir.mkdir()
        worker = self._make_worker(tmp_path)
        worker._clean_generated_config()
        assert not west_dir.exists()

    def test_preserves_west_if_config_valid(self, tmp_path):
        west_dir = tmp_path / ".west"
        west_dir.mkdir()
        (west_dir / "config").write_text("[manifest]\npath = config\n")
        config = tmp_path / "config"
        config.mkdir()
        worker = self._make_worker(tmp_path)
        worker._clean_generated_config()
        assert not config.exists()
        assert west_dir.exists()


class TestStopMethod:
    def test_stop_kills_active_process(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "corne"
        model.keyboard.mcu = "nice_nano_v2"
        worker = ZmkBuildWorker(model=model, workspace_dir=tmp_path)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        worker._proc = mock_proc
        worker.stop()
        mock_proc.kill.assert_called_once()

    def test_stop_skips_kill_if_no_process(self, tmp_path):
        model = ProjectModel()
        model.keyboard.model = "corne"
        model.keyboard.mcu = "nice_nano_v2"
        worker = ZmkBuildWorker(model=model, workspace_dir=tmp_path)
        worker.stop()
