"""OledWidget — onglet de personnalisation OLED.

Permet d'importer une image (PNG, BMP, GIF) et d'afficher une prévisualisation
pixel-perfect 64×128px en 1-bit noir et blanc, avec animation frame-by-frame
pour les GIF multi-frames (FR8, FR9).
La conversion est déléguée à processor.py (pur Python, sans Qt).
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.project_model import ProjectModel
from modules.oled_editor.processor import (
    OLED_HEIGHT,
    OLED_WIDTH,
    convert_image,
    convert_image_with_delays,
    get_frame_delays,
)

logger = logging.getLogger(__name__)

# Mapping objectName → identifiant overlay dans model.oled.overlays
_OVERLAY_IDS: dict[str, str] = {
    "layer_check": "layer",
    "caps_lock_check": "caps_lock",
    "wpm_check": "wpm",
}

# L1 — labels séparés de _OVERLAY_IDS pour éviter reconstruction dans la boucle
_OVERLAY_LABELS: dict[str, str] = {
    "layer_check": "Layer actif",
    "caps_lock_check": "Caps Lock",
    "wpm_check": "WPM",
}


class _ConversionWorker(QThread):
    """QThread pour la conversion image — délégué hors du thread UI."""

    finished = Signal(list, list)  # (list[bytes] frames, list[int] delays_ms)
    error = Signal(str)

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def run(self) -> None:
        try:
            # M1 : fichier ouvert une seule fois — garantit len(frames) == len(delays)
            frames, delays = convert_image_with_delays(self._path)
            # M2 : assertion explicite — transforme une désync silencieuse en erreur visible
            assert len(frames) == len(delays), (
                f"Désynchronisation frames/delays : {len(frames)} vs {len(delays)}"
            )
            self.finished.emit(frames, delays)
        except Exception as e:
            self.error.emit(str(e))


class OledWidget(QWidget):
    """Widget de l'onglet OLED.

    Contient un bouton d'import et une zone de prévisualisation QLabel.
    Met à jour model.oled.image_path et model.oled.frames après conversion.
    Anime les GIF multi-frames via QTimer avec intervalles variables.
    """

    def __init__(self, model: ProjectModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._worker: _ConversionWorker | None = None
        self._frame_delays: list[int] = []
        self._anim_idx: int = 0
        self._pending_path: str = ""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)
        self._setup_ui()
        self._sync_overlays_from_model()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._import_btn = QPushButton("Importer une image…")
        self._import_btn.setObjectName("import_btn")
        self._import_btn.clicked.connect(self._on_import_clicked)
        layout.addWidget(self._import_btn)

        self._preview_label = QLabel("Aucune image importée")
        self._preview_label.setObjectName("preview_label")
        self._preview_label.setMinimumSize(OLED_WIDTH * 3, OLED_HEIGHT * 3)
        layout.addWidget(self._preview_label)

        # Section overlays
        overlay_group = QGroupBox("Overlays")
        overlay_layout = QVBoxLayout(overlay_group)
        for obj_name in _OVERLAY_IDS:
            cb = QCheckBox(_OVERLAY_LABELS[obj_name])
            cb.setObjectName(obj_name)
            cb.stateChanged.connect(self._on_overlay_changed)
            overlay_layout.addWidget(cb)
        layout.addWidget(overlay_group)

        layout.addStretch()

    def _on_import_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer une image", str(Path.home()), "Images (*.png *.bmp *.gif)"
        )
        if not path:
            return
        # L2 — ignorer si un worker tourne encore (sécurité pour appels programmatiques)
        if self._worker and self._worker.isRunning():
            logger.warning("Import ignoré : un worker est déjà en cours d'exécution")
            return
        self._import_btn.setEnabled(False)
        self._worker = _ConversionWorker(Path(path))
        self._worker.finished.connect(self._on_conversion_done)
        self._worker.error.connect(self._on_conversion_error)
        self._worker.finished.connect(lambda *_: self._import_btn.setEnabled(True))
        self._worker.error.connect(lambda _: self._import_btn.setEnabled(True))
        self._worker.start()
        self._pending_path = path

    def _on_conversion_done(self, frames: list, delays: list) -> None:
        self._timer.stop()
        self._model.oled.image_path = self._pending_path
        self._model.oled.frames = frames
        self._frame_delays = delays
        self._anim_idx = 0
        self._show_frame(0)
        if len(frames) > 1:
            self._timer.setInterval(delays[0] if delays else 100)
            self._timer.start()
        logger.info("Import OLED terminé : %s (%d frame(s))", self._pending_path, len(frames))

    def _on_conversion_error(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur d'import", f"Impossible de charger l'image : {message}")
        logger.error("Erreur conversion OLED : %s", message)

    def _on_timer_tick(self) -> None:
        frames = self._model.oled.frames
        if not frames:
            self._timer.stop()
            return
        self._anim_idx = (self._anim_idx + 1) % len(frames)
        self._show_frame(self._anim_idx)
        # M2 — vérification des bornes avant accès : _frame_delays peut être plus court que frames
        if self._frame_delays and self._anim_idx < len(self._frame_delays):
            next_delay = self._frame_delays[self._anim_idx]
        else:
            next_delay = 100
        self._timer.setInterval(next_delay)

    def _on_overlay_changed(self) -> None:
        overlays = []
        for obj_name, overlay_id in _OVERLAY_IDS.items():
            cb = self.findChild(QCheckBox, obj_name)
            if cb and cb.isChecked():
                overlays.append(overlay_id)
        self._model.oled.overlays = overlays
        logger.info("Overlays mis à jour : %s", overlays)

    def _sync_overlays_from_model(self) -> None:
        """Synchronise les checkboxes depuis model.oled.overlays (ex : après chargement projet)."""
        for obj_name, overlay_id in _OVERLAY_IDS.items():
            cb = self.findChild(QCheckBox, obj_name)
            if cb:
                cb.blockSignals(True)
                cb.setChecked(overlay_id in self._model.oled.overlays)
                cb.blockSignals(False)

    def _show_frame(self, idx: int) -> None:
        frames = self._model.oled.frames
        if not frames or idx >= len(frames):
            return
        data = frames[idx]
        # M1 — valider la taille du buffer avant de construire QImage (buffer trop court → crash Qt)
        expected_size = OLED_WIDTH * OLED_HEIGHT
        if len(data) != expected_size:
            logger.warning(
                "Frame %d a une taille inattendue : %d octets (attendu %d) — ignorée",
                idx, len(data), expected_size,
            )
            return
        img = QImage(data, OLED_WIDTH, OLED_HEIGHT, OLED_WIDTH, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(img)
        self._preview_label.setPixmap(
            pixmap.scaled(OLED_WIDTH * 3, OLED_HEIGHT * 3, Qt.AspectRatioMode.KeepAspectRatio)
        )
