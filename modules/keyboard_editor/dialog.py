"""dialog — KleImportWidget pour la création de claviers custom.

Widget intégré comme onglet dans la fenêtre principale.
L'utilisateur dessine son clavier sur keyboard-layout-editor.com,
colle le JSON ici, et notre outil ajoute les infos matrice + hardware.
Sauvegarde dans ~/.keyboard_firmware_maker/custom_keyboards/{nom}.yaml.
"""
from __future__ import annotations

import json
import logging
import re
from itertools import groupby
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from modules.hardware.keyboard_loader import (
    KeyboardDefinition,
    KeyLayout,
    McuOption,
    McuPins,
)
from modules.keyboard_editor.kle_parser import KleKey, parse_kle_json
from modules.keyboard_editor.validator import validate_keyboard
from modules.keyboard_editor.yaml_exporter import export_keyboard

logger = logging.getLogger(__name__)

CUSTOM_DIR = Path.home() / ".keyboard_firmware_maker" / "custom_keyboards"
_VALID_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_BOOTLOADERS = ["rp2040", "caterina", "atmel-dfu", "stm32-dfu", "tinyuf2"]

# MCU bien connus de l'écosystème Vial/QMK — toujours proposés en preset
_WELL_KNOWN_MCUS: list[McuOption] = [
    McuOption(
        id="pro_micro",
        display_name="ATmega32U4 (Pro Micro)",
        description="Le plus courant (42.8% des claviers Vial). 5V/16MHz, 32KB flash.",
        bootloader="caterina",
    ),
    McuOption(
        id="rp2040",
        display_name="RP2040",
        description="Arm Cortex-M0+ dual-core (15.5% des claviers Vial). 264KB RAM, UF2.",
        bootloader="rp2040",
    ),
    McuOption(
        id="stm32f072",
        display_name="STM32F072",
        description="Arm Cortex-M0 (18% des claviers Vial). 128KB flash, USB natif.",
        bootloader="stm32-dfu",
    ),
    McuOption(
        id="stm32f103",
        display_name="STM32F103 (Blue Pill)",
        description="Arm Cortex-M3 (4% des claviers Vial). 64-128KB flash.",
        bootloader="stm32-dfu",
    ),
    McuOption(
        id="stm32f303",
        display_name="STM32F303 (Proton-C)",
        description="Arm Cortex-M4. Remplacement Pro Micro avec USB-C.",
        bootloader="stm32-dfu",
    ),
    McuOption(
        id="stm32f401",
        display_name="STM32F401 (WeAct Blackpill)",
        description="Arm Cortex-M4, 256KB flash, 84MHz.",
        bootloader="stm32-dfu",
    ),
    McuOption(
        id="stm32f411",
        display_name="STM32F411 (Blackpill v2)",
        description="Arm Cortex-M4, 512KB flash, 100MHz.",
        bootloader="stm32-dfu",
    ),
    McuOption(
        id="elite_c",
        display_name="Elite-C (ATmega32U4)",
        description="Pro Micro avec USB-C et bootloader atmel-dfu.",
        bootloader="atmel-dfu",
    ),
]

_PREVIEW_PX = 30  # pixels per unit in the preview canvas
_KEY_COLOR = QColor("#4A90D9")
_KEY_BORDER = QColor("#1C3A5E")


class KleImportWidget(QWidget):
    """Widget d'import KLE intégré comme onglet dans la fenêtre principale.

    Signaux :
        keyboard_saved(str) : émis après sauvegarde, avec le model_id du clavier.
    """

    keyboard_saved = Signal(str)

    def __init__(
        self,
        keyboards: list[KeyboardDefinition],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._keyboards = keyboards
        self._parsed_keys: list[KleKey] = []

        self._setup_ui()
        self._connect_signals()

    # ── Setup UI ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)

        # ── Zone gauche : KLE import + preview ────────────────────────
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # KLE JSON input
        kle_container = QWidget()
        kle_layout = QVBoxLayout(kle_container)
        kle_layout.setContentsMargins(0, 0, 0, 0)

        kle_header = QHBoxLayout()
        kle_label = QLabel(tr("keyboard_editor.kle_label"))
        kle_label.setStyleSheet("font-weight: bold;")
        kle_header.addWidget(kle_label)
        kle_header.addStretch()

        self._parse_btn = QPushButton(tr("keyboard_editor.parse_btn"))
        self._parse_btn.setObjectName("parse_btn")
        kle_header.addWidget(self._parse_btn)
        kle_layout.addLayout(kle_header)

        help_label = QLabel(tr("keyboard_editor.kle_help"))
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #AAA; font-size: 11px;")
        help_label.setOpenExternalLinks(True)
        kle_layout.addWidget(help_label)

        self._kle_text = QPlainTextEdit()
        self._kle_text.setObjectName("kle_text")
        self._kle_text.setPlaceholderText(tr("keyboard_editor.kle_placeholder"))
        kle_layout.addWidget(self._kle_text)

        self._parse_status = QLabel("")
        self._parse_status.setObjectName("parse_status")
        self._parse_status.setWordWrap(True)
        kle_layout.addWidget(self._parse_status)

        left_splitter.addWidget(kle_container)

        # Preview canvas (read-only)
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel(tr("keyboard_editor.preview_label"))
        preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_label)

        self._preview_scene = QGraphicsScene()
        self._preview_view = QGraphicsView(self._preview_scene)
        self._preview_view.setMinimumHeight(150)
        self._preview_view.setBackgroundBrush(QBrush(QColor("#2B2B2B")))
        self._preview_view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._preview_view.setInteractive(False)
        preview_layout.addWidget(self._preview_view)

        left_splitter.addWidget(preview_container)
        left_splitter.setStretchFactor(0, 2)
        left_splitter.setStretchFactor(1, 3)

        main_layout.addWidget(left_splitter, stretch=3)

        # ── Panneau propriétés (droite) ──────────────────────────────
        props_scroll = QScrollArea()
        props_scroll.setWidgetResizable(True)
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)

        # Nom du clavier
        name_form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setObjectName("name_edit")
        self._name_edit.setPlaceholderText("mon-clavier")
        name_form.addRow(tr("keyboard_editor.name_label"), self._name_edit)
        props_layout.addLayout(name_form)

        # Split
        self._split_check = QCheckBox()
        self._split_check.setObjectName("split_check")
        split_form = QFormLayout()
        split_form.addRow(tr("keyboard_editor.split_label"), self._split_check)
        props_layout.addLayout(split_form)

        # MCU
        mcu_box = QGroupBox(tr("keyboard_editor.section_mcu"))
        mcu_form = QFormLayout(mcu_box)

        seen_ids: set[str] = set()
        self._mcu_presets: list = []
        # 1. MCU well-known en priorité (ordre fixe, couverture écosystème)
        for mcu in _WELL_KNOWN_MCUS:
            if mcu.id not in seen_ids:
                seen_ids.add(mcu.id)
                self._mcu_presets.append(mcu)
        # 2. MCU additionnels depuis les claviers chargés
        for kb in self._keyboards:
            for mcu in kb.mcu_options:
                if mcu.id not in seen_ids:
                    seen_ids.add(mcu.id)
                    self._mcu_presets.append(mcu)
        self._mcu_preset_combo = QComboBox()
        self._mcu_preset_combo.setObjectName("mcu_preset_combo")
        self._mcu_preset_combo.addItem(tr("keyboard_editor.mcu_manual"))
        for mcu in self._mcu_presets:
            self._mcu_preset_combo.addItem(f"{mcu.display_name} ({mcu.id})")
        mcu_form.addRow(tr("keyboard_editor.mcu_preset"), self._mcu_preset_combo)

        self._mcu_id_edit = QLineEdit()
        self._mcu_id_edit.setObjectName("mcu_id_edit")
        self._mcu_id_edit.setPlaceholderText("rp2040")
        mcu_form.addRow(tr("keyboard_editor.mcu_id"), self._mcu_id_edit)
        self._mcu_name_edit = QLineEdit()
        self._mcu_name_edit.setObjectName("mcu_name_edit")
        self._mcu_name_edit.setPlaceholderText("RP2040")
        mcu_form.addRow(tr("keyboard_editor.mcu_name"), self._mcu_name_edit)
        self._mcu_boot_combo = QComboBox()
        self._mcu_boot_combo.setObjectName("mcu_boot_combo")
        for bl in _BOOTLOADERS:
            self._mcu_boot_combo.addItem(bl)
        mcu_form.addRow(tr("keyboard_editor.mcu_boot"), self._mcu_boot_combo)
        props_layout.addWidget(mcu_box)

        # Capacités
        caps_box = QGroupBox(tr("keyboard_editor.section_caps"))
        caps_form = QFormLayout(caps_box)
        self._oled_check = QCheckBox()
        self._oled_check.setObjectName("oled_check")
        caps_form.addRow(tr("keyboard_editor.oled"), self._oled_check)
        self._rgb_check = QCheckBox()
        self._rgb_check.setObjectName("rgb_check")
        caps_form.addRow(tr("keyboard_editor.rgb"), self._rgb_check)
        self._encoder_check = QCheckBox()
        self._encoder_check.setObjectName("encoder_check")
        caps_form.addRow(tr("keyboard_editor.encoder"), self._encoder_check)
        props_layout.addWidget(caps_box)

        # GPIO Pins (masqué par défaut)
        self._pins_toggle = QToolButton()
        self._pins_toggle.setText(tr("keyboard_editor.section_pins") + " \u25b6")
        self._pins_toggle.setObjectName("pins_toggle")
        self._pins_toggle.setCheckable(True)
        props_layout.addWidget(self._pins_toggle)

        self._pins_warning = QLabel("\u26a0  " + tr("keyboard_editor.pins_warning"))
        self._pins_warning.setWordWrap(True)
        self._pins_warning.setStyleSheet("color: #FFA500; font-size: 10px;")
        props_layout.addWidget(self._pins_warning)

        self._pins_box = QGroupBox()
        self._pins_box.setVisible(False)
        self._pins_box.setObjectName("pins_box")
        pins_form = QFormLayout(self._pins_box)
        self._pins_rows_edit = QLineEdit()
        self._pins_rows_edit.setObjectName("pins_rows_edit")
        self._pins_rows_edit.setPlaceholderText("GP0, GP1, GP2")
        pins_form.addRow(tr("keyboard_editor.pins_rows"), self._pins_rows_edit)
        self._pins_cols_edit = QLineEdit()
        self._pins_cols_edit.setObjectName("pins_cols_edit")
        self._pins_cols_edit.setPlaceholderText("GP10, GP11, GP12, GP13")
        pins_form.addRow(tr("keyboard_editor.pins_cols"), self._pins_cols_edit)
        self._pins_serial_edit = QLineEdit()
        self._pins_serial_edit.setObjectName("pins_serial_edit")
        self._pins_serial_edit.setPlaceholderText("GP1")
        pins_form.addRow(tr("keyboard_editor.pins_serial"), self._pins_serial_edit)
        self._pins_ws2812_edit = QLineEdit()
        self._pins_ws2812_edit.setObjectName("pins_ws2812_edit")
        self._pins_ws2812_edit.setPlaceholderText("GP0")
        pins_form.addRow(tr("keyboard_editor.pins_ws2812"), self._pins_ws2812_edit)
        props_layout.addWidget(self._pins_box)

        # Bouton Sauvegarder
        self._save_btn = QPushButton(tr("keyboard_editor.save"))
        self._save_btn.setObjectName("save_btn")
        props_layout.addWidget(self._save_btn)

        props_layout.addStretch()

        props_scroll.setWidget(props_widget)
        main_layout.addWidget(props_scroll, stretch=1)

    # ── Connexions ────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._parse_btn.clicked.connect(self._on_parse)
        self._pins_toggle.toggled.connect(self._on_pins_toggle)
        self._mcu_preset_combo.currentIndexChanged.connect(self._on_mcu_preset_changed)
        self._save_btn.clicked.connect(self._on_save)

    # ── API publique ─────────────────────────────────────────────────────────

    def update_keyboards(self, keyboards: list[KeyboardDefinition]) -> None:
        """Met à jour la liste des claviers (après rechargement)."""
        self._keyboards = keyboards

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_parse(self) -> None:
        """Parse le JSON KLE collé et met à jour la preview."""
        text = self._kle_text.toPlainText()
        result = parse_kle_json(text)

        if not result.ok:
            self._parse_status.setStyleSheet("color: #FF6B6B;")
            self._parse_status.setText("\n".join(result.errors))
            self._parsed_keys = []
            self._preview_scene.clear()
            return

        self._parsed_keys = result.keys
        n_keys = len(result.keys)
        n_with_matrix = sum(1 for k in result.keys if k.row >= 0 and k.col >= 0)
        n_auto = n_keys - n_with_matrix

        status_parts = [tr("keyboard_editor.parse_ok").format(n=n_keys)]
        if n_with_matrix > 0:
            status_parts.append(
                tr("keyboard_editor.parse_matrix_found").format(n=n_with_matrix)
            )
        if n_auto > 0:
            status_parts.append(
                tr("keyboard_editor.parse_auto_assign").format(n=n_auto)
            )

        self._parse_status.setStyleSheet("color: #6BCB77;")
        self._parse_status.setText(" \u2014 ".join(status_parts))

        self._update_preview()

    def _update_preview(self) -> None:
        """Redessine le canvas de preview avec les touches parsées."""
        self._preview_scene.clear()
        font = QFont()
        font.setPointSize(7)

        for key in self._parsed_keys:
            px = key.x * _PREVIEW_PX
            py = key.y * _PREVIEW_PX
            pw = key.w * _PREVIEW_PX - 2
            ph = key.h * _PREVIEW_PX - 2

            rect = QGraphicsRectItem(0, 0, pw, ph)
            rect.setPos(px, py)
            rect.setBrush(QBrush(_KEY_COLOR))
            rect.setPen(QPen(_KEY_BORDER, 1))

            if key.r != 0.0:
                rect.setTransformOriginPoint(pw / 2, ph / 2)
                rect.setRotation(key.r)

            self._preview_scene.addItem(rect)

            # Label
            label = f"R{key.row}C{key.col}" if key.row >= 0 else "?"
            text_item = self._preview_scene.addText(label, font)
            text_item.setDefaultTextColor(QColor("#FFFFFF"))
            text_item.setPos(px + 2, py + 1)

        self._preview_view.fitInView(
            self._preview_scene.sceneRect().adjusted(-10, -10, 10, 10),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def _on_mcu_preset_changed(self, index: int) -> None:
        if index <= 0:
            return
        mcu = self._mcu_presets[index - 1]
        self._mcu_id_edit.setText(mcu.id)
        self._mcu_name_edit.setText(mcu.display_name)
        idx = self._mcu_boot_combo.findText(mcu.bootloader)
        if idx >= 0:
            self._mcu_boot_combo.setCurrentIndex(idx)
        self._pins_rows_edit.setText(", ".join(mcu.pins.matrix_rows))
        self._pins_cols_edit.setText(", ".join(mcu.pins.matrix_cols))
        self._pins_serial_edit.setText(mcu.pins.serial_tx)
        self._pins_ws2812_edit.setText(mcu.pins.ws2812)

    def _on_pins_toggle(self, checked: bool) -> None:
        self._pins_box.setVisible(checked)
        arrow = "\u25bc" if checked else "\u25b6"
        self._pins_toggle.setText(tr("keyboard_editor.section_pins") + f" {arrow}")

    # ── Auto-assign row/col ──────────────────────────────────────────────────

    def _auto_assign_row_col(self, keys: list[KleKey]) -> None:
        """Auto-assigne row/col aux touches sans position matrice."""
        unfixed = [k for k in keys if k.row < 0 or k.col < 0]
        if not unfixed:
            return

        def y_group(k: KleKey) -> float:
            return round(k.y * 4) / 4

        sorted_keys = sorted(unfixed, key=lambda k: (y_group(k), k.x))
        used_rows = {k.row for k in keys if k.row >= 0}
        next_row = 0

        for _, group_iter in groupby(sorted_keys, key=y_group):
            while next_row in used_rows:
                next_row += 1
            row_keys = sorted(group_iter, key=lambda k: k.x)
            for col_idx, k in enumerate(row_keys):
                k.row = next_row
                k.col = col_idx
            used_rows.add(next_row)
            next_row += 1

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    def _validate_name(self, name: str) -> str | None:
        if not name:
            return tr("keyboard_editor.err_empty_name")
        if not _VALID_MODEL_RE.match(name):
            return tr("keyboard_editor.err_invalid_name")
        if any(kb.model == name for kb in self._keyboards):
            return tr("keyboard_editor.err_name_exists")
        dest = CUSTOM_DIR / f"{name}.yaml"
        if dest.exists():
            return tr("keyboard_editor.err_name_exists")
        return None

    def _build_keyboard_definition(self, name: str) -> KeyboardDefinition:
        """Construit un KeyboardDefinition depuis les touches parsées et le formulaire."""
        split = self._split_check.isChecked()

        def kle_to_layout(k: KleKey) -> KeyLayout:
            return KeyLayout(
                row=k.row, col=k.col,
                x=k.x, y=k.y,
                w=k.w, h=k.h,
                r=k.r,
                encoder=k.encoder,
            )

        keys = self._parsed_keys
        if split:
            if keys:
                max_x = max(k.x + k.w for k in keys)
                mid = max_x / 2
                left = [kle_to_layout(k) for k in keys if k.x + k.w / 2 < mid]
                right = [kle_to_layout(k) for k in keys if k.x + k.w / 2 >= mid]
                layout = {"left": left, "right": right}
            else:
                layout = {"left": [], "right": []}
        else:
            layout = {"keys": [kle_to_layout(k) for k in keys]}

        def _parse_pins_str(s: str) -> list[str]:
            return [p.strip() for p in s.split(",") if p.strip()]

        mcu = McuOption(
            id=self._mcu_id_edit.text().strip() or "rp2040",
            display_name=self._mcu_name_edit.text().strip() or "RP2040",
            description="",
            bootloader=self._mcu_boot_combo.currentText(),
            pins=McuPins(
                matrix_rows=_parse_pins_str(self._pins_rows_edit.text()),
                matrix_cols=_parse_pins_str(self._pins_cols_edit.text()),
                serial_tx=self._pins_serial_edit.text().strip(),
                ws2812=self._pins_ws2812_edit.text().strip(),
            ),
        )

        display_name = name.replace("-", " ").title()
        return KeyboardDefinition(
            model=name,
            display_name=display_name,
            vial_name=display_name,
            description="Clavier custom créé avec keyboard_firmware_maker",
            split=split,
            mcu_options=[mcu],
            capabilities={
                "oled": self._oled_check.isChecked(),
                "rgb": self._rgb_check.isChecked(),
            },
            has_encoder=self._encoder_check.isChecked(),
            layout=layout,
        )

    def _save_vial_json(self, name: str, kd: KeyboardDefinition) -> None:
        """Sauvegarde le vial.json natif à côté du YAML."""
        all_keys = []
        for side_keys in kd.layout.values():
            all_keys.extend(side_keys)

        rows = max((k.row for k in all_keys), default=0) + 1
        cols = max((k.col for k in all_keys), default=0) + 1
        if kd.split:
            rows *= 2

        vial_data = {
            "name": kd.vial_name,
            "vendorId": kd.vial_vid,
            "productId": kd.vial_pid,
            "matrix": {"rows": rows, "cols": cols},
            "layouts": {
                "keymap": self._build_kle_keymap(),
            },
        }

        dest = CUSTOM_DIR / f"{name}.vial.json"
        dest.write_text(json.dumps(vial_data, indent=2), encoding="utf-8")
        logger.info("vial.json sauvegardé : %s", dest)

    def _build_kle_keymap(self) -> list:
        """Reconstruit le keymap KLE avec les positions matrice assignées."""
        text = self._kle_text.toPlainText().strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            try:
                data = json.loads(f"[{text}]")
            except json.JSONDecodeError:
                return []

        if isinstance(data, dict):
            layouts = data.get("layouts", {})
            rows = layouts.get("keymap", [])
        elif isinstance(data, list):
            if data and isinstance(data[0], dict) and not isinstance(data[0], list):
                rows = data[1:]
            elif data and isinstance(data[0], list):
                rows = data
            else:
                rows = [data]
        else:
            return []

        key_map = {i: k for i, k in enumerate(self._parsed_keys)}

        result_rows = []
        key_idx = 0
        for row in rows:
            if not isinstance(row, list):
                continue
            result_row: list = []
            for item in row:
                if isinstance(item, dict):
                    result_row.append(item)
                elif isinstance(item, str):
                    if key_idx in key_map:
                        k = key_map[key_idx]
                        label = f"{k.row},{k.col}"
                        if k.encoder:
                            lines = [""] * 9 + ["e"]
                            lines[0] = label
                            label = "\n".join(lines)
                        result_row.append(label)
                    else:
                        result_row.append(item)
                    key_idx += 1
            result_rows.append(result_row)

        return result_rows

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        err = self._validate_name(name)
        if err:
            QMessageBox.warning(self, tr("keyboard_editor.err_empty_name"), err)
            return

        if not self._parsed_keys:
            QMessageBox.warning(
                self, tr("keyboard_editor.save"), tr("keyboard_editor.err_no_keys")
            )
            return

        self._auto_assign_row_col(self._parsed_keys)

        kd = self._build_keyboard_definition(name)

        vr = validate_keyboard(kd)
        if not vr.ok:
            msg = "\n".join(f"\u2022 {e}" for e in vr.errors)
            QMessageBox.critical(
                self,
                tr("keyboard_editor.validation_title"),
                tr("keyboard_editor.validation_errors") + "\n\n" + msg,
            )
            return
        if vr.warnings:
            msg = "\n".join(f"\u2022 {w}" for w in vr.warnings)
            resp = QMessageBox.warning(
                self,
                tr("keyboard_editor.validation_title"),
                tr("keyboard_editor.validation_warnings") + "\n\n" + msg
                + "\n\n" + tr("keyboard_editor.validation_continue"),
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            )
            if resp != QMessageBox.StandardButton.Ok:
                return

        try:
            dest = CUSTOM_DIR / f"{name}.yaml"
            export_keyboard(kd, dest)
            self._save_vial_json(name, kd)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self, tr("keyboard_editor.save"), str(exc)
            )
            return

        logger.info("Clavier custom sauvegardé : %s", dest)
        self.keyboard_saved.emit(name)


# Backward compatibility alias
CustomKeyboardEditorDialog = KleImportWidget
