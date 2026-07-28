"""zmk_builder.py — Compilation ZMK locale dans un QThread isolé.

Pattern parallèle à builder.py (QMK) :
1. Génère la config ZMK via ZmkTemplateGenerator dans un workspace cache partagé
2. Lance `west init -l config` + `west update` (une seule fois)
3. Lance `west build -s zmk/app -b <board> -- -DSHIELD=<shield> ...` par entrée build.yaml
4. Collecte les .uf2 produits

Signaux émis vers BuildWidget :
  progress  = Signal(int)        0-100
  log_line  = Signal(str)        ligne de log west/cmake
  success   = Signal(list)       liste de Path vers les .uf2 produits
  error     = Signal(str)        message d'erreur humanisé
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from PySide6.QtCore import QThread, Signal

from config import CACHE_DIR, ZMK_WORKSPACE_DIR
from models.project_model import ProjectModel
from modules.build_manager.proc_stream import (
    ProcInterruptedError,
    ProcTimeoutError,
    iter_lines_with_timeout,
)
from modules.build_manager.zmk_template_generator import ZmkTemplateGenerator

logger = logging.getLogger(__name__)


ZEPHYR_SDK_VERSION = "0.17.0"
ZEPHYR_SDK_DIR = CACHE_DIR / f"zephyr-sdk-{ZEPHYR_SDK_VERSION}"

# Regex pour la progression CMake/Ninja : "[42/123] ..."
_NINJA_PROGRESS_RE = re.compile(r"^\[(\d+)/(\d+)\]")

# Timeout global pour les commandes west longues (west update clone ~500 Mo)
_WEST_TIMEOUT_S = 1800  # 30 min

# Nombre de lignes attendu pour west update (estimation pour calcul progression)
_WEST_UPDATE_EXPECTED_LINES = 300


def is_zephyr_sdk_installed() -> bool:
    """Vérifie que le Zephyr SDK est présent avec le toolchain ARM installé."""
    toolchain_dir = ZEPHYR_SDK_DIR / "arm-zephyr-eabi"
    return ZEPHYR_SDK_DIR.is_dir() and toolchain_dir.is_dir()


def is_west_available() -> bool:
    """Vérifie que west est installé (via pip)."""
    try:
        subprocess.run(
            [sys.executable, "-m", "west", "--version"],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


class ZmkBuildWorker(QThread):
    """Thread de compilation ZMK — génère la config, lance west build par shield."""

    progress = Signal(int)      # 0-100
    log_line = Signal(str)
    success = Signal(list)      # list[Path] : .uf2 produits
    error = Signal(str)

    def __init__(
        self,
        model: ProjectModel,
        generator: ZmkTemplateGenerator | None = None,
        workspace_dir: Path = ZMK_WORKSPACE_DIR,
        skip_update: bool = False,
    ) -> None:
        super().__init__()
        self._model = model
        self._generator = generator or ZmkTemplateGenerator()
        self._workspace = workspace_dir
        self._skip_update = skip_update
        self._proc: subprocess.Popen | None = None

    def run(self) -> None:
        try:
            uf2_paths = self._build()
            if uf2_paths:
                self.success.emit(uf2_paths)
        except _InterruptedError:
            self.log_line.emit("[INFO] Compilation annulée.")
            self.error.emit("Compilation annulée par l'utilisateur.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur ZmkBuildWorker")
            self.error.emit(str(exc))

    def stop(self) -> None:
        """Demande l'arrêt du build et tue le sous-processus en cours."""
        self.requestInterruption()
        proc = self._proc
        if proc and proc.poll() is None:
            proc.kill()

    # ─────────────────────────────────────────────────────── Steps ──

    def _build(self) -> list[Path]:
        # 1. Vérifs prérequis (0-2 %)
        if not is_zephyr_sdk_installed():
            raise RuntimeError(
                f"Zephyr SDK introuvable dans {ZEPHYR_SDK_DIR}.\n"
                f"Lancez scripts/setup_zmk.{'bat' if sys.platform == 'win32' else 'sh'} pour l'installer."
            )
        if not is_west_available():
            raise RuntimeError(
                "west non disponible. Relancez start.sh/start.bat pour l'installer."
            )
        self.progress.emit(2)

        # 2. Génération config dans le workspace (2-10 %)
        self.log_line.emit("Génération de la config ZMK…")
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._clean_generated_config()
        generated = self._generator.generate(self._model, self._workspace)
        build_yaml = generated["build.yaml"]
        self.progress.emit(10)

        # 3. west init (10-12 %) — idempotent
        if not (self._workspace / ".west").is_dir():
            self.log_line.emit("Initialisation du workspace west (une seule fois)…")
            rc = self._run_west(["init", "-l", "config"], step="west init")
            if rc != 0:
                raise RuntimeError("west init a échoué. Consultez le log ci-dessus.")
        self.progress.emit(12)

        # 4. west update (12-55 %) — long au premier coup
        # Condition : on update si zmk/app ou zephyr/cmake manquent (update partiel précédent).
        if not self._skip_update and not self._is_workspace_updated():
            self.log_line.emit("Téléchargement de zmk + zephyr + modules (peut prendre plusieurs minutes)…")
            rc = self._run_west(["update"], step="west update", progress_range=(12, 55))
            if rc != 0:
                raise RuntimeError(
                    "west update a échoué (réseau ? espace disque ?). Consultez le log ci-dessus."
                )
        self.progress.emit(55)

        # 4b. west zephyr-export — enregistre Zephyr dans le registre CMake
        if not self._is_zephyr_exported():
            self.log_line.emit("Enregistrement de Zephyr dans CMake…")
            rc = self._run_west(["zephyr-export"], step="west zephyr-export")
            if rc != 0:
                raise RuntimeError("west zephyr-export a échoué. Consultez le log ci-dessus.")
        self.progress.emit(60)

        # 5. Parser build.yaml pour connaître les cibles
        entries = self._parse_build_yaml(build_yaml)
        if not entries:
            raise RuntimeError(f"Aucune cible dans {build_yaml}.")

        # 6. west build par cible (60-95 %)
        uf2_paths: list[Path] = []
        per_entry = (95 - 60) // len(entries)
        for i, entry in enumerate(entries):
            start = 60 + i * per_entry
            end = start + per_entry
            uf2 = self._build_one(entry, progress_range=(start, end))
            if uf2:
                uf2_paths.append(uf2)

        self.progress.emit(100)
        return uf2_paths

    def _clean_generated_config(self) -> None:
        """Supprime le dossier config/ existant avant régénération (évite résidus).

        Vérifie que .west/config est toujours cohérent ; sinon supprime .west/
        pour forcer un west init propre au prochain step.
        """
        config_dir = self._workspace / "config"
        if config_dir.is_dir():
            shutil.rmtree(config_dir)
        west_dir = self._workspace / ".west"
        west_cfg = west_dir / "config"
        if west_dir.is_dir() and not west_cfg.is_file():
            shutil.rmtree(west_dir)

    def _is_workspace_updated(self) -> bool:
        """Vrai si `west update` a réussi précédemment (zmk ET zephyr présents)."""
        return (
            (self._workspace / "zmk" / "app").is_dir()
            and (self._workspace / "zephyr" / "cmake").is_dir()
        )

    def _is_zephyr_exported(self) -> bool:
        """Vrai si `west zephyr-export` a déjà enregistré le package CMake."""
        cmake_pkg = Path.home() / ".cmake" / "packages" / "Zephyr"
        return cmake_pkg.is_dir() and any(cmake_pkg.iterdir())

    def _parse_build_yaml(self, path: Path) -> list[dict]:
        """Parse build.yaml et retourne la liste des cibles de compilation."""
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        entries = data.get("include", []) if isinstance(data, dict) else []
        return [e for e in entries if isinstance(e, dict) and e.get("board") and e.get("shield")]

    def _build_one(self, entry: dict, progress_range: tuple[int, int]) -> Path | None:
        """Compile un shield. Retourne le chemin du .uf2 ou None si échec."""
        board = entry["board"]
        shield = entry["shield"]
        snippet = entry.get("snippet")

        build_dir_name = shield.replace(" ", "_")
        build_dir = self._workspace / "build" / build_dir_name

        self.log_line.emit(f"Compilation {shield} pour {board}…")
        config_abs = str((self._workspace / "config").resolve())

        cmake_args = [
            f"-DSHIELD={shield}",
            f"-DZMK_CONFIG={config_abs}",
        ]
        if snippet:
            cmake_args.append(f"-DSNIPPET={snippet}")

        cmd = [
            "build",
            "-s", "zmk/app",
            "-d", str(build_dir),
            "-b", board,
            "--pristine", "auto",
            "--",
            *cmake_args,
        ]
        rc = self._run_west(cmd, step=f"west build {shield}", progress_range=progress_range)
        if rc != 0:
            raise RuntimeError(f"Compilation échouée pour {shield}.")

        uf2_candidates = sorted(
            (build_dir / "zephyr").glob("*.uf2"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ) if (build_dir / "zephyr").is_dir() else []
        if uf2_candidates:
            self.log_line.emit(f"  → {uf2_candidates[0]}")
            return uf2_candidates[0]

        self.log_line.emit(f"[WARN] Aucun .uf2 trouvé dans {build_dir / 'zephyr'}")
        return None

    def _run_west(
        self,
        args: list[str],
        step: str,
        progress_range: tuple[int, int] | None = None,
        timeout: int = _WEST_TIMEOUT_S,
    ) -> int:
        """Exécute une commande west dans le workspace, streamant les logs."""
        cmd = [sys.executable, "-m", "west", *args]
        env = self._env()
        logger.debug("Exec: %s (cwd=%s)", " ".join(cmd), self._workspace)

        proc = subprocess.Popen(
            cmd,
            cwd=str(self._workspace),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self._proc = proc
        line_count = 0

        try:
            try:
                # Lecture via thread + queue : timeout et annulation restent
                # effectifs même si west se fige sans émettre de sortie
                # (hang réseau pendant west update par exemple).
                for line in iter_lines_with_timeout(
                    proc, timeout, self.isInterruptionRequested
                ):
                    stripped = line.rstrip()
                    self.log_line.emit(stripped)
                    line_count += 1

                    if progress_range is not None:
                        lo, hi = progress_range
                        pct = _parse_ninja_progress(stripped)
                        if pct is not None:
                            self.progress.emit(lo + int(pct / 100 * (hi - lo)))
                        else:
                            fallback = min(95, int(line_count / _WEST_UPDATE_EXPECTED_LINES * 100))
                            self.progress.emit(lo + int(fallback / 100 * (hi - lo)))
            except ProcInterruptedError:
                raise _InterruptedError from None
            except ProcTimeoutError:
                self.log_line.emit(f"[ERREUR] {step} — timeout ({timeout}s) dépassé.")
                return -1

            proc.wait()
        finally:
            self._proc = None

        if proc.returncode != 0:
            self.log_line.emit(f"[ERREUR] {step} → code {proc.returncode}")
        return proc.returncode

    def _env(self) -> dict[str, str]:
        """Env var pour west : pointe vers le Zephyr SDK et la base Zephyr."""
        env = os.environ.copy()
        env["ZEPHYR_SDK_INSTALL_DIR"] = str(ZEPHYR_SDK_DIR)
        env["ZEPHYR_BASE"] = str(self._workspace / "zephyr")
        env.setdefault("ZEPHYR_TOOLCHAIN_VARIANT", "zephyr")
        return env


class _InterruptedError(Exception):
    """Levée quand le build est annulé via requestInterruption."""


def _parse_ninja_progress(line: str) -> int | None:
    """Extrait le pourcentage d'une ligne ninja : '[42/123] Building...'"""
    m = _NINJA_PROGRESS_RE.search(line)
    if not m:
        return None
    done, total = int(m.group(1)), int(m.group(2))
    if total <= 0:
        return None
    return min(100, int(done / total * 100))
