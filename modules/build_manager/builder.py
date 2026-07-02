"""builder.py — Compilation Vial-QMK dans un QThread isolé (FR16-FR20).

BuildWorker orchestre :
1. Génération du code source via TemplateGenerator
2. Lancement de make dans vial-qmk via subprocess
3. Parsing de la progression (0-100%) depuis les lignes make
4. Validation du .uf2 généré via Uf2ValidationResult

Signaux émis vers BuildWidget (thread UI) :
  progress  = Signal(int)   0-100
  log_line  = Signal(str)   ligne de log make
  success   = Signal(str)   chemin absolu du .uf2
  error     = Signal(str)   message d'erreur humanisé
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from models.project_model import ProjectModel
from modules.build_manager.error_classifier import classify_build_error
from modules.build_manager.msys2_manager import is_windows, resolve_make_env
from modules.build_manager.proc_stream import (
    ProcInterruptedError,
    ProcTimeoutError,
    iter_lines_with_timeout,
)
from modules.build_manager.template_generator import TemplateGenerator
from modules.build_manager.uf2_validator import validate_uf2

logger = logging.getLogger(__name__)

# Timeout global du make : un build QMK complet prend quelques minutes,
# 30 min couvre le pire cas (premier build MSYS2 sous Windows).
_MAKE_TIMEOUT_S = 1800

# Capacités flash par MCU (en octets)
MCU_FLASH: dict[str, int] = {
    "rp2040":    2 * 1024 * 1024,   # 2 MB
    "pro_micro": 28 * 1024,          # 32 KB - 4 KB bootloader
    "elite_c":   28 * 1024,
}

# Regexp pour extraire le pourcentage des lignes make QMK : "[  1%] ..."
_PROGRESS_RE = re.compile(r"\[\s*(\d+)%\]")

# Nom du clavier dans le répertoire vial-qmk
_QMK_KEYBOARD_NAME = "keyboard_firmware_maker"
_QMK_KEYMAP_NAME = "default"


class BuildWorker(QThread):
    """Thread de compilation — génère le code et exécute make."""

    progress = Signal(int)   # 0-100
    log_line = Signal(str)   # ligne de log make
    success  = Signal(str)   # chemin absolu du .uf2
    error    = Signal(str)   # message d'erreur humanisé

    def __init__(
        self,
        model: ProjectModel,
        vial_qmk_dir: Path,
        gcc_path: Path | None,
        generator: TemplateGenerator | None = None,
    ) -> None:
        super().__init__()
        self._model = model
        self._vial_qmk_dir = vial_qmk_dir
        self._gcc_path = gcc_path
        self._generator = generator or TemplateGenerator()
        self._log_lines: list[str] = []  # accumulé pour classify_build_error
        self._proc: subprocess.Popen | None = None

    def stop(self) -> None:
        """Demande l'arrêt du build et tue le sous-processus make en cours."""
        self.requestInterruption()
        proc = self._proc
        if proc and proc.poll() is None:
            proc.kill()

    def run(self) -> None:
        self._log_lines = []
        try:
            self._build()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur BuildWorker")
            diag = classify_build_error(self._log_lines)
            # M1 : toujours émettre un message lisible (FR21), jamais str(exc) brut
            self.error.emit(f"{diag.message}\n\n{diag.diagnosis}")
            logger.debug("Exception BuildWorker (détail) : %s", exc)

    def _build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = Path(tmp) / "keyboards" / _QMK_KEYBOARD_NAME
            src_dir.mkdir(parents=True)

            # 1. Génération du code source
            self.log_line.emit("Génération du code source QMK…")
            self._generator.generate(self._model, src_dir)
            self.progress.emit(10)
            self.log_line.emit("Code source QMK généré.")

            # 2. Copie dans vial-qmk
            kb_dest = self._vial_qmk_dir / "keyboards" / _QMK_KEYBOARD_NAME
            self._copy_sources(src_dir, kb_dest)
            self.log_line.emit(f"Sources copiées dans {kb_dest}")
            self.progress.emit(15)

            # 2b. Purger le build cache pour forcer la recompilation
            #     QMK ne détecte pas toujours les changements de config.h
            build_obj = self._vial_qmk_dir / ".build" / f"obj_{_QMK_KEYBOARD_NAME}_{_QMK_KEYMAP_NAME}"
            if build_obj.is_dir():
                shutil.rmtree(build_obj)
                logger.debug("Build cache purgé : %s", build_obj)

            # 3. Compilation
            self.log_line.emit("Lancement de la compilation…")
            uf2_path = self._run_make()

            # 4. Validation UF2 — si None, l'erreur a déjà été émise par _run_make()
            if uf2_path is None:
                return
            result = validate_uf2(uf2_path)
            if result.valid:
                self.progress.emit(100)
                self.log_line.emit(result.message)
                self.success.emit(str(uf2_path))
            else:
                self.error.emit(f"Firmware invalide : {result.message}")

    def _copy_sources(self, src: Path, dest: Path) -> None:
        """Copie le répertoire src dans dest (remplace si existant)."""
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)

    def _run_make(self) -> Path | None:
        """Lance `make keyboard_firmware_maker:default` et émet les signaux."""
        target = f"{_QMK_KEYBOARD_NAME}:{_QMK_KEYMAP_NAME}"

        try:
            make_base, env, shell_prefix = resolve_make_env(gcc_path=self._gcc_path)
        except FileNotFoundError as exc:
            self.error.emit(str(exc))
            return None

        if is_windows() and len(make_base) == 2 and make_base[1] == "-lc":
            # MSYS2 bash -lc : le wrapper qmk dans /usr/bin/ gère les checks Makefile
            # SKIP_GIT=true évite les git submodule checks qui échouent sous MSYS2
            cmd = [
                make_base[0], make_base[1],
                f"{shell_prefix}make SKIP_GIT=true -j4 {target}",
            ]
        else:
            cmd = [*make_base, "-j4", target]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self._vial_qmk_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
        except FileNotFoundError:
            self.error.emit(
                "La commande 'make' est introuvable. "
                "Installez les outils de compilation (make, arm-none-eabi-gcc)."
            )
            return None

        self._proc = proc
        try:
            # Lecture via thread + queue : annulation (stop()) et timeout
            # restent effectifs même si make se fige sans émettre de sortie.
            for line in iter_lines_with_timeout(
                proc, _MAKE_TIMEOUT_S, self.isInterruptionRequested
            ):
                stripped = line.rstrip()
                self._log_lines.append(stripped)
                self.log_line.emit(stripped)
                pct = _parse_progress(stripped)
                if pct is not None:
                    # Remap [0-100] make → [15-95] total
                    remapped = 15 + int(pct * 0.80)
                    self.progress.emit(remapped)
        except ProcInterruptedError:
            self.log_line.emit("[INFO] Compilation annulée.")
            self.error.emit("Compilation annulée par l'utilisateur.")
            return None
        except ProcTimeoutError:
            self.error.emit(
                f"Compilation interrompue : make sans réponse après "
                f"{_MAKE_TIMEOUT_S // 60} minutes. Réessayez."
            )
            return None
        finally:
            self._proc = None

        proc.wait()

        if proc.returncode != 0:
            diag = classify_build_error(self._log_lines)
            self.error.emit(f"{diag.message}\n\n{diag.diagnosis}")
            return None

        # M2 : chercher le .uf2 le plus récent (tri par mtime décroissant)
        candidates = sorted(
            self._vial_qmk_dir.rglob("*.uf2"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]

        self.error.emit(
            "Fichier .uf2 introuvable après compilation. "
            "Vérifiez les logs ci-dessus."
        )
        return None


def _parse_progress(line: str) -> int | None:
    """Extrait le pourcentage d'une ligne make QMK, ex : '[  42%] Building...'"""
    m = _PROGRESS_RE.search(line)
    return int(m.group(1)) if m else None
