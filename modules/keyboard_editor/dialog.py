"""dialog — CustomKeyboardEditorDialog pour la création de claviers custom.

Dialog modal avec canvas QGraphicsScene (scène unique) et panneau propriétés.
Sauvegarde dans ~/.keyboard_firmware_maker/custom_keyboards/{nom}.yaml.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
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
from modules.keyboard_editor.canvas import GRID_PX, KeyboardCanvas, KeyItem
from modules.keyboard_editor.yaml_exporter import export_keyboard

logger = logging.getLogger(__name__)

CUSTOM_DIR = Path.home() / ".keyboard_firmware_maker" / "custom_keyboards"
_VALID_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_BOOTLOADERS = ["rp2040", "caterina", "atmel-dfu"]


class CustomKeyboardEditorDialog(QDialog):
    """Dialog d'édition de clavier custom.

    Attributs publics après accept() :
        saved_model_id (str) : slug du clavier sauvegardé.
    """

    def __init__(
        self,
        keyboards: list[KeyboardDefinition],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._keyboards = keyboards
        self.saved_model_id: str = ""

        self.setWindowTitle(tr("keyboard_editor.title"))
        self.setMinimumSize(1100, 650)

        self._setup_ui()
        self._connect_signals()

    # ── Setup UI ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)

        # ── Zone canvas (gauche) ─────────────────────────────────────────
        canvas_container = QVBoxLayout()
        canvas_container.addLayout(self._build_canvas_toolbar())
        self._canvas = KeyboardCanvas(self)
        canvas_container.addWidget(self._canvas)
        main_layout.addLayout(canvas_container, stretch=3)

        # ── Panneau propriétés (droite) ──────────────────────────────────
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

        # GPIO Pins (masqué par défaut — S2)
        self._pins_toggle = QToolButton()
        self._pins_toggle.setText(tr("keyboard_editor.section_pins") + " ▶")
        self._pins_toggle.setObjectName("pins_toggle")
        self._pins_toggle.setCheckable(True)
        props_layout.addWidget(self._pins_toggle)

        self._pins_warning = QLabel("⚠  " + tr("keyboard_editor.pins_warning"))
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

        props_layout.addStretch()

        props_scroll.setWidget(props_widget)
        main_layout.addWidget(props_scroll, stretch=1)

        # ── Boutons bas ──────────────────────────────────────────────────
        buttons_layout = QVBoxLayout()
        self._save_btn = QPushButton(tr("keyboard_editor.save"))
        self._save_btn.setObjectName("save_btn")
        self._save_btn.setDefault(True)
        self._cancel_btn = QPushButton(tr("keyboard_editor.cancel"))
        self._cancel_btn.setObjectName("cancel_btn")
        buttons_layout.addWidget(self._save_btn)
        buttons_layout.addWidget(self._cancel_btn)
        main_layout.addLayout(buttons_layout)

    def _build_canvas_toolbar(self) -> QHBoxLayout:
        """Construit la barre d'outils au-dessus du canvas."""
        toolbar = QHBoxLayout()

        base_label = QLabel(tr("keyboard_editor.base_label"))
        self._base_combo = QComboBox()
        self._base_combo.setObjectName("base_combo")
        self._base_combo.addItem(tr("keyboard_editor.base_empty"))
        for kb in self._keyboards:
            self._base_combo.addItem(kb.display_name)
        toolbar.addWidget(base_label)
        toolbar.addWidget(self._base_combo)

        self._import_pcb_btn = QPushButton(tr("keyboard_editor.import_pcb"))
        self._import_pcb_btn.setObjectName("import_pcb_btn")
        toolbar.addWidget(self._import_pcb_btn)

        self._delete_image_btn = QPushButton(tr("keyboard_editor.delete_image"))
        self._delete_image_btn.setObjectName("delete_image_btn")
        toolbar.addWidget(self._delete_image_btn)

        self._snap_check = QCheckBox(tr("keyboard_editor.snap_grid"))
        self._snap_check.setObjectName("snap_check")
        self._snap_check.setChecked(True)
        toolbar.addWidget(self._snap_check)

        self._add_key_btn = QPushButton(tr("keyboard_editor.add_key"))
        self._add_key_btn.setObjectName("add_key_btn")
        toolbar.addWidget(self._add_key_btn)

        self._delete_key_btn = QPushButton(tr("keyboard_editor.delete_key"))
        self._delete_key_btn.setObjectName("delete_key_btn")
        toolbar.addWidget(self._delete_key_btn)

        toolbar.addStretch()
        return toolbar

    # ── Connexions ────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._pins_toggle.toggled.connect(self._on_pins_toggle)
        self._base_combo.currentIndexChanged.connect(self._on_base_changed)
        self._split_check.toggled.connect(self._on_split_toggled)
        self._import_pcb_btn.clicked.connect(self._on_import_pcb)
        self._delete_image_btn.clicked.connect(self._canvas.remove_background_images)
        self._snap_check.toggled.connect(self._on_snap_toggled)
        self._add_key_btn.clicked.connect(self._on_add_key)
        self._delete_key_btn.clicked.connect(self._canvas.remove_selected)
        self._oled_check.toggled.connect(self._on_oled_toggled)
        self._encoder_check.toggled.connect(self._on_encoder_toggled)
        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_pins_toggle(self, checked: bool) -> None:
        self._pins_box.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self._pins_toggle.setText(tr("keyboard_editor.section_pins") + f" {arrow}")

    def _on_base_changed(self, index: int) -> None:
        """Charge le layout du clavier sélectionné dans le canvas."""
        self._canvas.clear_keys()
        self._canvas.remove_background_images()

        if index == 0:
            # Canvas vide — réinitialiser aussi les indicateurs
            self._canvas.set_oled_indicators(False, False)
            self._canvas.set_encoder_indicator(False, False)
            return

        kb = self._keyboards[index - 1]  # -1 car index 0 = "Canvas vide"

        # Mettre à jour split selon le clavier de base
        self._split_check.blockSignals(True)
        self._split_check.setChecked(kb.split)
        self._split_check.blockSignals(False)
        if kb.split:
            self._canvas.add_split_separator()
        else:
            self._canvas.remove_split_separator()

        # Charger le layout
        if kb.split:
            self._canvas.load_from_layout(kb.layout.get("left", []), side="left")
            self._canvas.load_from_layout(kb.layout.get("right", []), side="right")
        else:
            keys = kb.layout.get("keys", [])
            if not keys and kb.layout_variants:
                keys = kb.layout_variants[0].keys
            self._canvas.load_from_layout(keys, side="keys")

        # Pré-remplir propriétés MCU depuis le clavier de base (J1)
        if kb.mcu_options:
            mcu = kb.mcu_options[0]
            self._mcu_id_edit.setText(mcu.id)
            self._mcu_name_edit.setText(mcu.display_name)
            idx = self._mcu_boot_combo.findText(mcu.bootloader)
            if idx >= 0:
                self._mcu_boot_combo.setCurrentIndex(idx)
            # Pré-remplir pins
            pins = mcu.pins
            self._pins_rows_edit.setText(", ".join(pins.matrix_rows))
            self._pins_cols_edit.setText(", ".join(pins.matrix_cols))
            self._pins_serial_edit.setText(pins.serial_tx)
            self._pins_ws2812_edit.setText(pins.ws2812)

        # Pré-remplir capacités
        self._oled_check.setChecked(bool(kb.capabilities.get("oled", False)))
        self._rgb_check.setChecked(bool(kb.capabilities.get("rgb", False)))
        self._encoder_check.setChecked(kb.has_encoder)

        # Mettre à jour les indicateurs visuels
        self._canvas.set_oled_indicators(bool(kb.capabilities.get("oled", False)), kb.split)
        self._canvas.set_encoder_indicator(kb.has_encoder, kb.split)

    def _on_split_toggled(self, checked: bool) -> None:
        """Gère le basculement split/non-split."""
        if not checked:
            # Vérifier si des touches droite existent
            right_keys = self._canvas.get_keys(side="right")
            if right_keys:
                reply = QMessageBox.question(
                    self,
                    tr("keyboard_editor.split_label"),
                    tr("keyboard_editor.split_clear_warning"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    self._split_check.blockSignals(True)
                    self._split_check.setChecked(True)
                    self._split_check.blockSignals(False)
                    return
                self._canvas.clear_keys(side="right")
            self._canvas.remove_split_separator()
        else:
            self._canvas.add_split_separator()

        # Mettre à jour les indicateurs visuels selon le nouveau mode split
        self._canvas.set_oled_indicators(self._oled_check.isChecked(), checked)
        self._canvas.set_encoder_indicator(self._encoder_check.isChecked(), checked)

    def _on_import_pcb(self) -> None:
        # Titre sans ellipse pour la boîte de dialogue (F11)
        title = tr("keyboard_editor.import_pcb").rstrip("\u2026").rstrip(".")
        path, _ = QFileDialog.getOpenFileName(
            self, title, str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not path:
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(
                self,
                tr("dlg.error"),
                tr("oled.import_error_msg").format(msg=Path(path).name),
            )
            return

        # Scaler pour tenir raisonnablement dans le canvas
        pixmap = pixmap.scaled(
            560, 400,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._canvas.remove_background_images()
        self._canvas.add_pcb_image(pixmap, x_offset_px=0)

        # Proposer de dupliquer en miroir pour la moitié droite (split)
        if self._split_check.isChecked():
            reply = QMessageBox.question(
                self,
                tr("keyboard_editor.pcb_duplicate_title"),
                tr("keyboard_editor.pcb_duplicate_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                mirrored = pixmap.transformed(QTransform().scale(-1, 1))
                separator_px = 7 * GRID_PX
                self._canvas.add_pcb_image(mirrored, x_offset_px=separator_px)

    def _on_oled_toggled(self, checked: bool) -> None:
        self._canvas.set_oled_indicators(checked, self._split_check.isChecked())

    def _on_encoder_toggled(self, checked: bool) -> None:
        self._canvas.set_encoder_indicator(checked, self._split_check.isChecked())

    def _on_snap_toggled(self, checked: bool) -> None:
        self._canvas.snap_enabled = checked

    def _on_add_key(self) -> None:
        """Ajoute une touche à la première position libre du canvas."""
        side = "left" if self._split_check.isChecked() else "keys"
        # Trouver une position y libre (en bas des touches existantes)
        existing = self._canvas.get_keys(side)
        if existing:
            max_y = max(round(it.pos().y() / GRID_PX) for it in existing)
            next_y = max_y + 1
        else:
            next_y = 0
        self._canvas.add_key(x_u=0.0, y_u=float(next_y), side=side)

    # ── Sauvegarde ────────────────────────────────────────────────────────────

    def _validate_name(self, name: str) -> str | None:
        """Retourne un message d'erreur ou None si valide."""
        if not name:
            return tr("keyboard_editor.err_empty_name")
        if not _VALID_MODEL_RE.match(name):
            return tr("keyboard_editor.err_invalid_name")
        # Vérifier doublons parmi tous les claviers chargés (prédéfinis + customs)
        if any(kb.model == name for kb in self._keyboards):
            return tr("keyboard_editor.err_name_exists")
        dest = CUSTOM_DIR / f"{name}.yaml"
        if dest.exists():
            return tr("keyboard_editor.err_name_exists")
        return None

    def _auto_assign_row_col(self, items: list[KeyItem]) -> None:
        """Auto-assigne row/col aux items non fixés (tri y→x, groupes par ligne).

        Les items sur la même ligne y (même y-grid) reçoivent le même row,
        et des col séquentiels 0, 1, 2... de gauche à droite.
        """
        unfixed = [it for it in items if not it.manually_fixed]
        if not unfixed:
            return

        # Grouper par y-grid (arrondi à GRID_PX)
        from itertools import groupby
        sorted_by_yx = sorted(
            unfixed,
            key=lambda k: (round(k.pos().y() / GRID_PX), round(k.pos().x() / GRID_PX)),
        )
        used_rows = {it.row for it in items if it.manually_fixed and it.row >= 0}
        next_row = 0
        for y_grid, group_iter in groupby(sorted_by_yx, key=lambda k: round(k.pos().y() / GRID_PX)):
            while next_row in used_rows:
                next_row += 1
            row_items = sorted(group_iter, key=lambda k: k.pos().x())
            for col_idx, it in enumerate(row_items):
                it.row = next_row
                it.col = col_idx
            used_rows.add(next_row)
            next_row += 1

    def _build_keyboard_definition(self, name: str) -> KeyboardDefinition:
        """Construit un KeyboardDefinition depuis le canvas et le formulaire."""
        split = self._split_check.isChecked()

        # Collecter les touches par side
        def items_to_layouts(items: list[KeyItem]) -> list[KeyLayout]:
            result = []
            for it in sorted(
                items,
                key=lambda k: (round(k.pos().y() / GRID_PX), round(k.pos().x() / GRID_PX)),
            ):
                result.append(KeyLayout(
                    row=it.row,
                    col=it.col,
                    x=round(it.pos().x() / GRID_PX, 2),
                    y=round(it.pos().y() / GRID_PX, 2),
                    w=it.w_u,
                    h=it.h_u,
                ))
            return result

        if split:
            layout = {
                "left": items_to_layouts(self._canvas.get_keys("left")),
                "right": items_to_layouts(self._canvas.get_keys("right")),
            }
        else:
            layout = {"keys": items_to_layouts(self._canvas.get_keys("keys"))}

        # MCU
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

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        err = self._validate_name(name)
        if err:
            QMessageBox.warning(self, tr("keyboard_editor.err_empty_name"), err)
            return

        all_keys = self._canvas.get_keys()
        if not all_keys:
            QMessageBox.warning(
                self, tr("keyboard_editor.save"), tr("keyboard_editor.err_no_keys")
            )
            return

        self._auto_assign_row_col(all_keys)

        kd = self._build_keyboard_definition(name)

        try:
            dest = CUSTOM_DIR / f"{name}.yaml"
            export_keyboard(kd, dest)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self, tr("keyboard_editor.save"), str(exc)
            )
            return

        self.saved_model_id = name
        logger.info("Clavier custom sauvegardé : %s", dest)
        self.accept()
