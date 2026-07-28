"""AdvancedOptionsWidget — onglet KFM "Options avancées".

Expose ~25 options ZMK/QMK avancées (NKRO, BLE passkey, tap-dance, sticky keys,
RGB start, mousekeys, etc.) regroupées par sections thématiques. Les options
non concernées par le firmware courant restent **visibles mais grisées** avec
un tooltip explicatif.

Voir le catalogue complet :
  ~/.claude/projects/.../memory/firmware_options_catalog.md
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from models.project_model import ProjectModel
from modules.keymap_importer.common import (
    FORMAT_UNKNOWN,
    FORMAT_VIAL,
    FORMAT_ZMK,
    ConversionReport,
    detect_format,
)
from ui.tooltips import apply_tooltips, tooltip_for

logger = logging.getLogger(__name__)

# Champs documentés par une infobulle (clé i18n `tip.<objectName>`).
ADVANCED_TOOLTIP_FIELDS = [
    "adv_use_custom_keymap", "adv_keymap_import_btn",
    "adv_keyboard_name",
    "adv_nkro_enabled", "adv_hid_indicators_enabled", "adv_usb_boot_protocol",
    "adv_auto_shift_enabled", "adv_auto_shift_timeout_ms",
    "adv_ble_passkey_entry",
    "adv_deep_sleep_timeout_min", "adv_battery_report_interval_s", "adv_soft_off_enabled",
    "adv_tap_dance_enabled", "adv_sticky_key_enabled", "adv_tapping_term_ms",
    "adv_combo_term_ms", "adv_permissive_hold",
    "adv_rgb_hue_start", "adv_rgb_on_start", "adv_rgb_auto_off_idle", "adv_rgb_auto_off_usb",
    "adv_pointing_enabled", "adv_pointing_smooth_scroll",
    "adv_mousekey_enabled", "adv_mousekey_delay_ms", "adv_mousekey_interval_ms",
    "adv_mousekey_max_speed",
]


class AdvancedOptionsWidget(QWidget):
    """Onglet d'options avancées QMK/ZMK.

    Architecture :
    - QScrollArea verticale (toutes les options visibles, scroll si besoin)
    - 8 QGroupBox thématiques empilées
    - Chaque champ référence un attribut de `model.advanced` via objectName
    - `set_firmware()` grise les sections non applicables avec tooltip
    """

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._firmware = "qmk"  # défaut, sera updaté par MainWindow

        # Widgets référencés par firmware-compatibility pour le greying.
        # Chaque entry = (widget, ("zmk", "qmk") supportés).
        self._firmware_compat: list[tuple[QWidget, tuple[str, ...]]] = []

        # Layout racine = scroll area enveloppant un container vertical
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setSpacing(12)

        self._build_section_keymap_import()
        self._build_section_identification()
        self._build_section_keyboard_behavior()
        self._build_section_bluetooth()
        self._build_section_energy()
        self._build_section_ergo()
        self._build_section_rgb_advanced()
        self._build_section_pointing()
        self._build_section_mouse_keys()

        self._container_layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)

        apply_tooltips(self, ADVANCED_TOOLTIP_FIELDS)
        self._sync_from_model()

    # ── Sections ─────────────────────────────────────────────────────────────

    def _build_section_keymap_import(self) -> None:
        """Import d'un keymap existant — première section de l'onglet.

        Accepte un export vial.rocks (.vil/.json) ou un keymap ZMK (.keymap),
        quel que soit le firmware cible : la conversion croisée est faite à
        l'import et ce qui n'est pas transposable est signalé.
        """
        group = QGroupBox(tr("adv.section.keymap_import"))
        v = QVBoxLayout(group)

        self._keymap_use = QCheckBox(tr("adv.keymap.use"))
        self._keymap_use.setObjectName("adv_use_custom_keymap")
        self._keymap_use.setChecked(bool(self._model.keyboard.use_custom_keymap))
        self._keymap_use.stateChanged.connect(self._on_use_keymap_changed)
        v.addWidget(self._keymap_use)

        row = QHBoxLayout()
        self._keymap_btn = QPushButton(tr("adv.keymap.import_btn"))
        self._keymap_btn.setObjectName("adv_keymap_import_btn")
        self._keymap_btn.setEnabled(bool(self._model.keyboard.use_custom_keymap))
        self._keymap_btn.clicked.connect(self._on_import_keymap_clicked)
        row.addWidget(self._keymap_btn)

        self._keymap_status = QLabel(self._keymap_status_text())
        self._keymap_status.setObjectName("adv_keymap_status")
        self._keymap_status.setStyleSheet("color: #888; font-size: 11px;")
        row.addWidget(self._keymap_status, 1)
        v.addLayout(row)

        info = QLabel(tr("adv.keymap.help"))
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 10px;")
        v.addWidget(info)

        self._container_layout.addWidget(group)

    def _build_section_identification(self) -> None:
        group = QGroupBox(tr("adv.section.identification"))
        form = QFormLayout(group)

        self._keyboard_name = QLineEdit()
        self._keyboard_name.setObjectName("adv_keyboard_name")
        # 16 max : limite ZMK pour le nom d'advertising BLE (build cassé au-delà)
        self._keyboard_name.setMaxLength(16)
        self._keyboard_name.setPlaceholderText(tr("adv.keyboard_name.placeholder"))
        self._keyboard_name.textChanged.connect(self._on_keyboard_name_changed)
        form.addRow(QLabel(tr("adv.keyboard_name.label")), self._keyboard_name)

        info = QLabel(tr("adv.keyboard_name.help"))
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 10px;")
        form.addRow(info)

        self._container_layout.addWidget(group)
        # ZMK uniquement : mappé à CONFIG_ZMK_KEYBOARD_NAME. Le générateur QMK
        # prend le nom depuis le YAML du clavier (vial_name), pas depuis ce champ.
        self._firmware_compat.append((group, ("zmk",)))

    def _build_section_keyboard_behavior(self) -> None:
        group = QGroupBox(tr("adv.section.keyboard_behavior"))
        v = QVBoxLayout(group)

        self._nkro = self._make_check("adv_nkro_enabled", tr("adv.nkro"))
        v.addWidget(self._nkro)

        # HID indicators et Boot Protocol : Kconfig ZMK uniquement. QMK les gère
        # nativement, décocher ici n'aurait aucun effet sur le firmware généré.
        self._hid_indicators = self._make_check(
            "adv_hid_indicators_enabled", tr("adv.hid_indicators"), firmware_only=("zmk",)
        )
        v.addWidget(self._hid_indicators)

        self._usb_boot = self._make_check(
            "adv_usb_boot_protocol", tr("adv.usb_boot"), firmware_only=("zmk",)
        )
        v.addWidget(self._usb_boot)

        # Auto-shift QMK uniquement
        self._auto_shift = self._make_check(
            "adv_auto_shift_enabled", tr("adv.auto_shift"), firmware_only=("qmk",)
        )
        v.addWidget(self._auto_shift)

        as_row = QHBoxLayout()
        as_row.addWidget(QLabel(tr("adv.auto_shift_timeout")))
        self._auto_shift_spin = QSpinBox()
        self._auto_shift_spin.setObjectName("adv_auto_shift_timeout_ms")
        self._auto_shift_spin.setRange(50, 1000)
        self._auto_shift_spin.setValue(175)
        self._auto_shift_spin.setSuffix(" ms")
        self._auto_shift_spin.valueChanged.connect(self._on_auto_shift_timeout_changed)
        as_row.addWidget(self._auto_shift_spin)
        as_row.addStretch()
        as_container = QWidget()
        as_container.setLayout(as_row)
        v.addWidget(as_container)
        self._firmware_compat.append((as_container, ("qmk",)))

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("qmk", "zmk")))

    def _build_section_bluetooth(self) -> None:
        group = QGroupBox(tr("adv.section.bluetooth"))
        v = QVBoxLayout(group)

        self._ble_passkey = self._make_check(
            "adv_ble_passkey_entry", tr("adv.ble_passkey"), firmware_only=("zmk",)
        )
        v.addWidget(self._ble_passkey)

        info = QLabel(tr("adv.ble_passkey.help"))
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; font-size: 10px;")
        v.addWidget(info)

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("zmk",)))

    def _build_section_energy(self) -> None:
        group = QGroupBox(tr("adv.section.energy"))
        form = QFormLayout(group)

        self._deep_sleep_spin = QSpinBox()
        self._deep_sleep_spin.setObjectName("adv_deep_sleep_timeout_min")
        self._deep_sleep_spin.setRange(1, 60)
        self._deep_sleep_spin.setValue(4)
        self._deep_sleep_spin.setSuffix(" min")
        self._deep_sleep_spin.valueChanged.connect(self._on_deep_sleep_changed)
        form.addRow(QLabel(tr("adv.deep_sleep_timeout")), self._deep_sleep_spin)
        self._firmware_compat.append((self._deep_sleep_spin, ("zmk",)))

        self._battery_interval_spin = QSpinBox()
        self._battery_interval_spin.setObjectName("adv_battery_report_interval_s")
        self._battery_interval_spin.setRange(10, 600)
        self._battery_interval_spin.setValue(60)
        self._battery_interval_spin.setSuffix(" s")
        self._battery_interval_spin.valueChanged.connect(self._on_battery_interval_changed)
        form.addRow(QLabel(tr("adv.battery_report_interval")), self._battery_interval_spin)
        self._firmware_compat.append((self._battery_interval_spin, ("zmk",)))

        self._soft_off = self._make_check(
            "adv_soft_off_enabled", tr("adv.soft_off"), firmware_only=("zmk",)
        )
        form.addRow(self._soft_off)

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("qmk", "zmk")))

    def _build_section_ergo(self) -> None:
        group = QGroupBox(tr("adv.section.ergo"))
        v = QVBoxLayout(group)

        self._tap_dance = self._make_check("adv_tap_dance_enabled", tr("adv.tap_dance"))
        v.addWidget(self._tap_dance)

        self._sticky_key = self._make_check("adv_sticky_key_enabled", tr("adv.sticky_key"))
        v.addWidget(self._sticky_key)

        tap_row = QHBoxLayout()
        tap_row.addWidget(QLabel(tr("adv.tapping_term")))
        self._tapping_term_spin = QSpinBox()
        self._tapping_term_spin.setObjectName("adv_tapping_term_ms")
        self._tapping_term_spin.setRange(50, 1000)
        self._tapping_term_spin.setValue(200)
        self._tapping_term_spin.setSuffix(" ms")
        self._tapping_term_spin.valueChanged.connect(self._on_tapping_term_changed)
        tap_row.addWidget(self._tapping_term_spin)
        tap_row.addStretch()
        tap_container = QWidget()
        tap_container.setLayout(tap_row)
        v.addWidget(tap_container)
        self._firmware_compat.append((tap_container, ("qmk",)))

        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel(tr("adv.combo_term")))
        self._combo_term_spin = QSpinBox()
        self._combo_term_spin.setObjectName("adv_combo_term_ms")
        self._combo_term_spin.setRange(10, 500)
        self._combo_term_spin.setValue(50)
        self._combo_term_spin.setSuffix(" ms")
        self._combo_term_spin.valueChanged.connect(self._on_combo_term_changed)
        combo_row.addWidget(self._combo_term_spin)
        combo_row.addStretch()
        combo_container = QWidget()
        combo_container.setLayout(combo_row)
        v.addWidget(combo_container)
        self._firmware_compat.append((combo_container, ("qmk",)))

        self._permissive_hold = self._make_check(
            "adv_permissive_hold", tr("adv.permissive_hold"), firmware_only=("qmk",)
        )
        v.addWidget(self._permissive_hold)

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("qmk", "zmk")))

    def _build_section_rgb_advanced(self) -> None:
        group = QGroupBox(tr("adv.section.rgb_advanced"))
        v = QVBoxLayout(group)

        hue_row = QHBoxLayout()
        hue_row.addWidget(QLabel(tr("adv.rgb_hue_start")))
        self._rgb_hue_spin = QSpinBox()
        self._rgb_hue_spin.setObjectName("adv_rgb_hue_start")
        self._rgb_hue_spin.setRange(0, 359)
        self._rgb_hue_spin.setValue(0)
        self._rgb_hue_spin.setSuffix("°")
        self._rgb_hue_spin.valueChanged.connect(self._on_rgb_hue_changed)
        hue_row.addWidget(self._rgb_hue_spin)
        hue_row.addStretch()
        hue_container = QWidget()
        hue_container.setLayout(hue_row)
        v.addWidget(hue_container)
        self._firmware_compat.append((hue_container, ("zmk",)))

        self._rgb_on_start = self._make_check(
            "adv_rgb_on_start", tr("adv.rgb_on_start"), firmware_only=("zmk",)
        )
        v.addWidget(self._rgb_on_start)

        self._rgb_auto_off_idle = self._make_check(
            "adv_rgb_auto_off_idle", tr("adv.rgb_auto_off_idle"), firmware_only=("zmk",)
        )
        v.addWidget(self._rgb_auto_off_idle)

        self._rgb_auto_off_usb = self._make_check(
            "adv_rgb_auto_off_usb", tr("adv.rgb_auto_off_usb"), firmware_only=("zmk",)
        )
        v.addWidget(self._rgb_auto_off_usb)

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("zmk",)))

    def _build_section_pointing(self) -> None:
        group = QGroupBox(tr("adv.section.pointing"))
        v = QVBoxLayout(group)

        self._pointing_enabled = self._make_check(
            "adv_pointing_enabled", tr("adv.pointing"), firmware_only=("zmk",)
        )
        v.addWidget(self._pointing_enabled)

        self._pointing_smooth = self._make_check(
            "adv_pointing_smooth_scroll",
            tr("adv.pointing_smooth_scroll"),
            firmware_only=("zmk",),
        )
        v.addWidget(self._pointing_smooth)

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("zmk",)))

    def _build_section_mouse_keys(self) -> None:
        group = QGroupBox(tr("adv.section.mouse_keys"))
        form = QFormLayout(group)

        self._mk_enabled = self._make_check("adv_mousekey_enabled", tr("adv.mousekey_enabled"))
        form.addRow(self._mk_enabled)

        self._mk_delay_spin = QSpinBox()
        self._mk_delay_spin.setObjectName("adv_mousekey_delay_ms")
        self._mk_delay_spin.setRange(1, 200)
        self._mk_delay_spin.setValue(10)
        self._mk_delay_spin.setSuffix(" ms")
        self._mk_delay_spin.valueChanged.connect(self._on_mk_delay_changed)
        form.addRow(QLabel(tr("adv.mousekey_delay")), self._mk_delay_spin)

        self._mk_interval_spin = QSpinBox()
        self._mk_interval_spin.setObjectName("adv_mousekey_interval_ms")
        self._mk_interval_spin.setRange(1, 200)
        self._mk_interval_spin.setValue(20)
        self._mk_interval_spin.setSuffix(" ms")
        self._mk_interval_spin.valueChanged.connect(self._on_mk_interval_changed)
        form.addRow(QLabel(tr("adv.mousekey_interval")), self._mk_interval_spin)

        self._mk_speed_spin = QSpinBox()
        self._mk_speed_spin.setObjectName("adv_mousekey_max_speed")
        self._mk_speed_spin.setRange(1, 100)
        self._mk_speed_spin.setValue(10)
        self._mk_speed_spin.valueChanged.connect(self._on_mk_speed_changed)
        form.addRow(QLabel(tr("adv.mousekey_max_speed")), self._mk_speed_spin)

        self._container_layout.addWidget(group)
        self._firmware_compat.append((group, ("qmk",)))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_check(
        self,
        attr_name: str,
        label: str,
        firmware_only: tuple[str, ...] = ("qmk", "zmk"),
    ) -> QCheckBox:
        cb = QCheckBox(label)
        cb.setObjectName(attr_name)
        cb.stateChanged.connect(
            lambda state, name=attr_name: self._on_check_changed(name, bool(state))
        )
        if firmware_only != ("qmk", "zmk"):
            self._firmware_compat.append((cb, firmware_only))
        return cb

    # ── Import de keymap ─────────────────────────────────────────────────────

    def _keymap_status_text(self) -> str:
        """Décrit le keymap actuellement chargé (origine + nombre de couches)."""
        keymap = self._model.keyboard.custom_keymap
        if not keymap:
            return tr("adv.keymap.no_file")
        if isinstance(keymap.get("zmk_layers"), list):
            return tr("adv.keymap.loaded_zmk").format(n=len(keymap["zmk_layers"]))
        return tr("adv.keymap.loaded_vial").format(n=len(keymap.get("layout") or []))

    def _on_use_keymap_changed(self, state: int) -> None:
        enabled = bool(state)
        self._model.keyboard.use_custom_keymap = enabled
        self._keymap_btn.setEnabled(enabled)

    def _on_import_keymap_clicked(self) -> None:
        """Charge un keymap, avertit si son origine diffère du firmware cible."""
        path_str, _ = QFileDialog.getOpenFileName(
            self, tr("adv.keymap.dialog_title"), "", tr("adv.keymap.filter"),
        )
        if not path_str:
            return
        path = Path(path_str)

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(
                self, tr("adv.keymap.error_title"), tr("adv.keymap.error_msg").format(exc=exc),
            )
            return

        fmt = detect_format(path, content)
        if fmt == FORMAT_UNKNOWN:
            QMessageBox.warning(
                self, tr("adv.keymap.unknown_title"), tr("adv.keymap.unknown_msg"),
            )
            return

        # Origine ≠ firmware cible : prévenir avant de convertir, la conversion
        # est nécessairement partielle.
        if not self._confirm_cross_format(fmt):
            return

        keymap, report = self._load_keymap(path, content, fmt)
        if keymap is None:
            return

        self._model.keyboard.custom_keymap = keymap
        self._model.keyboard.use_custom_keymap = True
        self._keymap_use.setChecked(True)
        self._keymap_btn.setEnabled(True)
        self._keymap_status.setText(self._keymap_status_text())
        logger.info("Keymap importé (%s) : %s", fmt, path.name)
        self._show_report(fmt, report)

    def _confirm_cross_format(self, fmt: str) -> bool:
        """Demande confirmation quand le fichier ne vient pas du firmware cible."""
        if fmt == FORMAT_ZMK and self._firmware == "qmk":
            message = tr("adv.keymap.cross_zmk_to_qmk")
        elif fmt == FORMAT_VIAL and self._firmware == "zmk":
            message = tr("adv.keymap.cross_vial_to_zmk")
        else:
            return True
        reply = QMessageBox.question(
            self,
            tr("adv.keymap.cross_title"),
            message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Ok

    def _load_keymap(
        self, path: Path, content: str, fmt: str,
    ) -> tuple[dict | None, ConversionReport]:
        """Transforme le fichier en structure stockable dans le ProjectModel."""
        report = ConversionReport()
        if fmt == FORMAT_VIAL:
            try:
                return json.loads(content), report
            except json.JSONDecodeError as exc:
                QMessageBox.critical(
                    self, tr("adv.keymap.error_title"), tr("adv.keymap.error_msg").format(exc=exc),
                )
                return None, report

        from modules.keymap_importer.zmk_to_qmk import convert_zmk_layers_to_qmk, parse_zmk_keymap

        layers = parse_zmk_keymap(content)
        if not layers:
            QMessageBox.warning(
                self, tr("adv.keymap.unknown_title"), tr("adv.keymap.zmk_no_layer"),
            )
            return None, report
        # La conversion vers QMK n'est utile que pour une cible QMK, mais on la
        # joue dans tous les cas : elle produit le rapport des pertes.
        if self._firmware == "qmk":
            _, report = convert_zmk_layers_to_qmk(layers)
        return {"zmk_layers": layers}, report

    def _show_report(self, fmt: str, report: ConversionReport) -> None:
        """Affiche le bilan de conversion (silencieux si rien n'a été perdu)."""
        if not report.has_losses:
            QMessageBox.information(
                self,
                tr("adv.keymap.report_title"),
                tr("adv.keymap.report_ok").format(n=report.converted),
            )
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("adv.keymap.report_title"))
        box.setText(
            tr("adv.keymap.report_partial").format(
                converted=report.converted, dropped=len(report.dropped),
            )
        )
        details = list(report.warnings)
        details += [
            tr("adv.keymap.report_line").format(
                layer=d.layer, position=d.position, source=d.source, reason=d.reason,
            )
            for d in report.dropped
        ]
        box.setDetailedText("\n".join(details))
        box.exec()

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_check_changed(self, attr_name: str, state: bool) -> None:
        # attr_name = "adv_xxx_yyy" → on retire le préfixe "adv_" pour atteindre le modèle
        model_attr = attr_name[4:] if attr_name.startswith("adv_") else attr_name
        if hasattr(self._model.advanced, model_attr):
            setattr(self._model.advanced, model_attr, state)
            logger.info("Options avancées : %s = %s", model_attr, state)

    def _on_keyboard_name_changed(self, text: str) -> None:
        self._model.advanced.keyboard_name = text.strip()

    def _on_deep_sleep_changed(self, value: int) -> None:
        self._model.advanced.deep_sleep_timeout_min = max(1, value)

    def _on_battery_interval_changed(self, value: int) -> None:
        self._model.advanced.battery_report_interval_s = max(10, value)

    def _on_auto_shift_timeout_changed(self, value: int) -> None:
        self._model.advanced.auto_shift_timeout_ms = max(50, value)

    def _on_tapping_term_changed(self, value: int) -> None:
        self._model.advanced.tapping_term_ms = max(50, value)

    def _on_combo_term_changed(self, value: int) -> None:
        self._model.advanced.combo_term_ms = max(10, value)

    def _on_rgb_hue_changed(self, value: int) -> None:
        self._model.advanced.rgb_hue_start = max(0, min(359, value))

    def _on_mk_delay_changed(self, value: int) -> None:
        self._model.advanced.mousekey_delay_ms = max(1, value)

    def _on_mk_interval_changed(self, value: int) -> None:
        self._model.advanced.mousekey_interval_ms = max(1, value)

    def _on_mk_speed_changed(self, value: int) -> None:
        self._model.advanced.mousekey_max_speed = max(1, value)

    # ── Synchronisation modèle → UI ──────────────────────────────────────────

    def _sync_from_model(self) -> None:
        """Rafraîchit l'UI depuis le modèle (chargement projet, etc.)."""
        adv = self._model.advanced

        # Keymap importé (porté par model.keyboard, pas model.advanced)
        use_keymap = bool(self._model.keyboard.use_custom_keymap)
        self._keymap_use.blockSignals(True)
        self._keymap_use.setChecked(use_keymap)
        self._keymap_use.blockSignals(False)
        self._keymap_btn.setEnabled(use_keymap)
        self._keymap_status.setText(self._keymap_status_text())

        # Texte
        self._keyboard_name.blockSignals(True)
        self._keyboard_name.setText(adv.keyboard_name)
        self._keyboard_name.blockSignals(False)

        # Checkboxes
        for attr, cb in [
            ("nkro_enabled", self._nkro),
            ("hid_indicators_enabled", self._hid_indicators),
            ("usb_boot_protocol", self._usb_boot),
            ("auto_shift_enabled", self._auto_shift),
            ("ble_passkey_entry", self._ble_passkey),
            ("soft_off_enabled", self._soft_off),
            ("tap_dance_enabled", self._tap_dance),
            ("sticky_key_enabled", self._sticky_key),
            ("permissive_hold", self._permissive_hold),
            ("rgb_on_start", self._rgb_on_start),
            ("rgb_auto_off_idle", self._rgb_auto_off_idle),
            ("rgb_auto_off_usb", self._rgb_auto_off_usb),
            ("pointing_enabled", self._pointing_enabled),
            ("pointing_smooth_scroll", self._pointing_smooth),
            ("mousekey_enabled", self._mk_enabled),
        ]:
            cb.blockSignals(True)
            cb.setChecked(bool(getattr(adv, attr)))
            cb.blockSignals(False)

        # Spinboxes
        for attr, sp in [
            ("auto_shift_timeout_ms", self._auto_shift_spin),
            ("deep_sleep_timeout_min", self._deep_sleep_spin),
            ("battery_report_interval_s", self._battery_interval_spin),
            ("tapping_term_ms", self._tapping_term_spin),
            ("combo_term_ms", self._combo_term_spin),
            ("rgb_hue_start", self._rgb_hue_spin),
            ("mousekey_delay_ms", self._mk_delay_spin),
            ("mousekey_interval_ms", self._mk_interval_spin),
            ("mousekey_max_speed", self._mk_speed_spin),
        ]:
            sp.blockSignals(True)
            sp.setValue(int(getattr(adv, attr)))
            sp.blockSignals(False)

    def reload_from_model(self) -> None:
        """API publique : rafraîchir après un chargement de projet."""
        self._sync_from_model()

    # ── Firmware switching (greying) ─────────────────────────────────────────

    def set_firmware(self, firmware: str) -> None:
        """Grise les options non applicables au firmware courant.

        Les widgets restent visibles (choix UX du user) mais désactivés. Leur
        infobulle explicative est conservée : la mention « ZMK uniquement »
        s'ajoute en tête plutôt que de remplacer l'explication.
        """
        self._firmware = firmware
        for widget, compat in self._firmware_compat:
            enabled = firmware in compat
            widget.setEnabled(enabled)
            explanation = tooltip_for(widget.objectName())
            if enabled:
                widget.setToolTip(explanation)
                continue
            only = "QMK" if "qmk" in compat else "ZMK"
            notice = tr("adv.tooltip.firmware_only").format(firmware=only)
            widget.setToolTip(f"{notice}\n\n{explanation}" if explanation else notice)
