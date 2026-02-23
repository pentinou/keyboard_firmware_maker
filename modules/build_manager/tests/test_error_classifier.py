"""Tests pour modules/build_manager/error_classifier.py."""
from __future__ import annotations

import pytest

from modules.build_manager.error_classifier import ErrorDiagnosis, classify_build_error


class TestClassifyBuildError:
    def test_empty_log_returns_generic(self):
        result = classify_build_error([])
        assert result.pattern_matched is None
        assert "échoué" in result.message.lower() or "compilation" in result.message.lower()

    def test_unknown_log_returns_generic(self):
        result = classify_build_error(["some unknown build output", "nothing special"])
        assert result.pattern_matched is None

    def test_toolchain_missing_pattern(self):
        log = ["arm-none-eabi-gcc: command not found", "make: *** [all] Error 127"]
        result = classify_build_error(log)
        assert result.pattern_matched == "toolchain_missing"
        assert "toolchain" in result.message.lower() or "arm" in result.message.lower()
        assert result.diagnosis  # non vide

    def test_toolchain_not_found_variant(self):
        log = ["make: arm-none-eabi-gcc: No such file or directory"]
        result = classify_build_error(log)
        assert result.pattern_matched == "toolchain_missing"

    def test_syntax_error_pattern(self):
        log = [
            "keymap.c:12:5: error: unknown type name 'rgb_effect_t'",
            "make: *** [keymap.o] Error 1",
        ]
        result = classify_build_error(log)
        assert result.pattern_matched == "syntax_error"
        assert "syntaxe" in result.message.lower() or "syntax" in result.message.lower()

    def test_linker_error_pattern(self):
        log = [
            "keymap.o: undefined reference to 'rgb_matrix_set_color_all'",
            "collect2: error: ld returned 1 exit status",
        ]
        result = classify_build_error(log)
        assert result.pattern_matched == "linker_error"
        assert "liaison" in result.message.lower() or "linker" in result.message.lower()

    def test_flash_overflow_pattern(self):
        log = ["region `flash' overflowed by 12345 bytes"]
        result = classify_build_error(log)
        assert result.pattern_matched == "flash_overflow"
        assert "volumineux" in result.message.lower() or "firmware" in result.message.lower()

    def test_flash_overflow_alternative(self):
        log = ["firmware too large: 32768 > 28672"]
        result = classify_build_error(log)
        assert result.pattern_matched == "flash_overflow"

    def test_make_target_missing_pattern(self):
        log = ["make: No rule to make target 'keyboard_firmware_maker:default'"]
        result = classify_build_error(log)
        assert result.pattern_matched == "make_target_missing"

    def test_template_error_pattern(self):
        log = ["jinja2.exceptions.TemplateNotFound: keymap.c.j2"]
        result = classify_build_error(log)
        assert result.pattern_matched == "template_error"

    def test_permission_error_pattern(self):
        log = ["cannot open output file /root/build: permission denied"]
        result = classify_build_error(log)
        assert result.pattern_matched == "permission_error"

    def test_first_matching_pattern_wins(self):
        """Si plusieurs patterns matchent, le premier dans la liste gagne."""
        log = [
            "arm-none-eabi-gcc: command not found",
            "undefined reference to foo",
        ]
        result = classify_build_error(log)
        assert result.pattern_matched == "toolchain_missing"

    def test_diagnosis_is_non_empty(self):
        """Tout résultat doit avoir un diagnostic non vide."""
        for log in [
            [],
            ["arm-none-eabi-gcc: command not found"],
            ["error: unknown type name 'foo'"],
        ]:
            result = classify_build_error(log)
            assert result.diagnosis

    def test_error_diagnosis_is_dataclass(self):
        result = classify_build_error([])
        assert isinstance(result, ErrorDiagnosis)
        assert hasattr(result, "message")
        assert hasattr(result, "diagnosis")
        assert hasattr(result, "pattern_matched")


class TestBuilderUsesClassifier:
    """Vérifie l'intégration de classify_build_error dans BuildWorker."""

    def _model(self):
        from models.project_model import ProjectModel
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        m.keyboard.mcu = "rp2040"
        return m

    def test_make_failure_emits_classified_error(self, qtbot, tmp_path):
        """make returncode != 0 → error signal contient le message du classifier."""
        from unittest.mock import MagicMock, patch
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        errors: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.return_value = {}

        mock_proc = MagicMock()
        mock_proc.stdout = iter([
            "arm-none-eabi-gcc: command not found\n",
            "make: *** Error 127\n",
        ])
        mock_proc.returncode = 127
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
        # Le message doit venir du classifier (FR21) — lisible, pas le log brut gcc
        assert "toolchain" in errors[0].lower()

    def test_generator_exception_emits_error_not_crash(self, qtbot, tmp_path):
        """Si le generator lève une exception, error est émis (AC: 4)."""
        from unittest.mock import MagicMock
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        errors: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.side_effect = RuntimeError("Template boom")

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.error.connect(errors.append)
        worker.run()

        # Aucune exception ne doit remonter, le signal error doit être émis
        assert len(errors) == 1

    def test_generator_exception_emits_readable_message_not_raw_exc(self, qtbot, tmp_path):
        """M1 — exception sans pattern matché → message générique lisible, pas str(exc) (FR21)."""
        from unittest.mock import MagicMock
        from modules.build_manager.builder import BuildWorker
        from modules.build_manager.template_generator import TemplateGenerator

        errors: list[str] = []
        gen = MagicMock(spec=TemplateGenerator)
        gen.generate.side_effect = RuntimeError("Template boom internal detail")

        worker = BuildWorker(
            model=self._model(),
            vial_qmk_dir=tmp_path,
            gcc_path=None,
            generator=gen,
        )
        worker.error.connect(errors.append)
        worker.run()

        # Le message brut Python NE doit PAS apparaître (FR21)
        assert "Template boom internal detail" not in errors[0]
        # Le message générique du classifier doit être présent
        assert "compilation" in errors[0].lower() or "échoué" in errors[0].lower()


class TestBuildWidgetStatus:
    @pytest.fixture
    def widget(self, qtbot):
        from modules.build_manager.widget import BuildWidget
        from models.project_model import ProjectModel
        m = ProjectModel()
        m.keyboard.model = "sofle-v2"
        w = BuildWidget(m)
        qtbot.addWidget(w)
        return w

    def test_status_label_exists(self, widget):
        from PySide6.QtWidgets import QLabel
        lbl = widget.findChild(QLabel, "lbl_build_status")
        assert lbl is not None

    def test_error_updates_status_label(self, widget):
        from PySide6.QtWidgets import QLabel
        from unittest.mock import patch
        with patch("modules.build_manager.widget.QMessageBox.critical"):
            widget._on_build_error("Erreur test")
        lbl = widget.findChild(QLabel, "lbl_build_status")
        assert "Échec" in lbl.text() or "compilation" in lbl.text().lower()

    def test_button_reenabled_after_error(self, widget):
        from unittest.mock import patch
        widget._btn_build.setEnabled(False)
        with patch("modules.build_manager.widget.QMessageBox.critical"):
            widget._on_build_error("some error")
        assert widget._btn_build.isEnabled()

    def test_build_log_populated_after_error(self, widget):
        """AC1 — les logs QMK bruts restent accessibles dans build_log après erreur."""
        from PySide6.QtWidgets import QPlainTextEdit
        from unittest.mock import patch

        # Simuler quelques lignes de log comme si make les avait émises
        widget._log.appendPlainText("arm-none-eabi-gcc: command not found")
        widget._log.appendPlainText("make: *** Error 127")

        with patch("modules.build_manager.widget.QMessageBox.critical"):
            widget._on_build_error("La toolchain ARM est introuvable.")

        lbl_log = widget.findChild(QPlainTextEdit, "build_log")
        assert lbl_log is not None
        assert "arm-none-eabi-gcc" in lbl_log.toPlainText()
        assert "Error 127" in lbl_log.toPlainText()

    def test_build_log_not_cleared_on_error(self, widget):
        """AC1 — _on_build_error ne doit pas effacer les logs bruts."""
        from unittest.mock import patch

        widget._log.appendPlainText("raw qmk log line")
        with patch("modules.build_manager.widget.QMessageBox.critical"):
            widget._on_build_error("Erreur")

        assert "raw qmk log line" in widget._log.toPlainText()
