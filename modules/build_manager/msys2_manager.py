"""msys2_manager.py — Gestion de l'environnement MSYS2 pour Windows.

Fournit make + bash sous Windows pour compiler QMK.
Télécharge une installation MSYS2 minimale au premier lancement,
cachée dans ~/.keyboard_firmware_maker/msys2/.

Pattern identique à VialQmkManager : logique pure + QThread + QDialog.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import urlretrieve

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from i18n import tr

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".keyboard_firmware_maker"
MSYS2_DIR = CACHE_DIR / "msys2"

# URL de l'archive MSYS2 base (sans IDE, ~90 MB compressé)
# sfx = self-extracting archive, mais on traite le .tar.zst / .sfx.exe
MSYS2_RELEASE_BASE = "https://github.com/msys2/msys2-installer/releases/download"
MSYS2_VERSION = "2024-01-13"
MSYS2_ARCHIVE = f"msys2-base-x86_64-{MSYS2_VERSION.replace('-', '')}.sfx.exe"
MSYS2_URL = f"{MSYS2_RELEASE_BASE}/{MSYS2_VERSION}/{MSYS2_ARCHIVE}"

# Paquets minimaux nécessaires pour compiler QMK
MSYS2_PACKAGES = ["make", "bash", "coreutils"]


def is_windows() -> bool:
    """Retourne True si on tourne sous Windows natif (pas WSL)."""
    return sys.platform == "win32"


class Msys2Manager:
    """Gère la présence et l'installation de MSYS2 dans le cache local."""

    def is_ready(self) -> bool:
        """Vérifie que MSYS2 est installé avec make disponible."""
        make_path = self.get_make_path()
        return make_path is not None and make_path.is_file()

    def get_bash_path(self) -> Path | None:
        """Retourne le chemin vers bash.exe MSYS2, ou None si absent."""
        bash = MSYS2_DIR / "usr" / "bin" / "bash.exe"
        return bash if bash.is_file() else None

    def get_make_path(self) -> Path | None:
        """Retourne le chemin vers make.exe MSYS2, ou None si absent."""
        make = MSYS2_DIR / "usr" / "bin" / "make.exe"
        return make if make.is_file() else None

    def install(
        self,
        progress_callback: Callable[[int], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Télécharge et installe MSYS2 minimal.

        Args:
            progress_callback: appelé avec un entier 0-100.
            log_callback: appelé avec un message texte.

        Raises:
            subprocess.CalledProcessError: si une commande échoue.
            OSError: si le téléchargement ou l'extraction échoue.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        def _log(msg: str) -> None:
            logger.info(msg)
            if log_callback:
                log_callback(msg)

        # Nettoyage éventuel d'une installation incomplète
        if MSYS2_DIR.exists():
            shutil.rmtree(MSYS2_DIR)

        archive_path = CACHE_DIR / MSYS2_ARCHIVE

        # Étape 1 — Téléchargement (0 → 60%)
        _log("Téléchargement de MSYS2…")
        if progress_callback:
            progress_callback(5)

        def _report_progress(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and progress_callback:
                pct = min(int(block_num * block_size / total_size * 55), 55)
                progress_callback(5 + pct)

        urlretrieve(MSYS2_URL, str(archive_path), reporthook=_report_progress)
        if progress_callback:
            progress_callback(60)

        # Étape 2 — Extraction (60 → 80%)
        _log("Extraction de MSYS2…")
        _extract_msys2(archive_path, CACHE_DIR)
        if progress_callback:
            progress_callback(80)

        # Renommer le dossier extrait (msys64 → msys2)
        extracted = CACHE_DIR / "msys64"
        if extracted.is_dir():
            extracted.rename(MSYS2_DIR)

        # Nettoyage de l'archive
        archive_path.unlink(missing_ok=True)

        # Étape 3 — Initialisation et installation des paquets (80 → 95%)
        _log("Installation des paquets (make, bash, coreutils)…")
        bash = MSYS2_DIR / "usr" / "bin" / "bash.exe"
        if not bash.is_file():
            raise FileNotFoundError(f"bash.exe introuvable après extraction : {bash}")

        # Initialisation des clés pacman
        _run_msys2_cmd(bash, "pacman-key --init")
        _run_msys2_cmd(bash, "pacman-key --populate msys2")
        if progress_callback:
            progress_callback(85)

        # Installation des paquets nécessaires
        pkg_list = " ".join(MSYS2_PACKAGES)
        _run_msys2_cmd(bash, f"pacman -S --noconfirm --needed {pkg_list}")
        if progress_callback:
            progress_callback(95)

        # Vérification finale
        make = MSYS2_DIR / "usr" / "bin" / "make.exe"
        if not make.is_file():
            raise FileNotFoundError(f"make.exe introuvable après installation : {make}")

        if progress_callback:
            progress_callback(100)
        _log("MSYS2 prêt.")
        logger.info("MSYS2 installé dans %s", MSYS2_DIR)


def _extract_msys2(archive_path: Path, dest: Path) -> None:
    """Extrait l'archive MSYS2 (sfx.exe, tar, ou zip)."""
    name = archive_path.name.lower()

    if name.endswith(".sfx.exe"):
        # Self-extracting exe : lancer avec -y -o<dest>
        subprocess.run(
            [str(archive_path), "-y", f"-o{dest}"],
            check=True,
            capture_output=True,
        )
    elif name.endswith(".tar.xz") or name.endswith(".tar.gz"):
        with tarfile.open(archive_path) as tar:
            tar.extractall(path=dest)
    elif name.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(path=dest)
    else:
        # Tentative sfx comme fallback
        subprocess.run(
            [str(archive_path), "-y", f"-o{dest}"],
            check=True,
            capture_output=True,
        )


def _run_msys2_cmd(bash_path: Path, command: str) -> None:
    """Exécute une commande dans le shell MSYS2."""
    env_path = str(bash_path.parent.parent.parent)
    subprocess.run(
        [str(bash_path), "-lc", command],
        check=True,
        capture_output=True,
        text=True,
        env={
            "HOME": str(Path.home()),
            "MSYSTEM": "MSYS",
            "PATH": f"{env_path}/usr/bin",
        },
    )


def _win_to_msys2_path(win_path: str) -> str:
    """Convertit un chemin Windows en chemin MSYS2.

    ``C:\\Users\\foo\\bar`` → ``/c/Users/foo/bar``
    """
    p = win_path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        return "/" + p[0].lower() + p[2:]
    return p


def resolve_make_env(
    msys2_mgr: Msys2Manager | None = None,
    gcc_path: Path | None = None,
) -> tuple[list[str], dict[str, str], str]:
    """Résout la commande make et l'environnement selon la plateforme.

    Sur Windows, QMK requiert un shell Unix (bash) pour les pipes et
    utilitaires (tr, qmk). On passe TOUJOURS par MSYS2 bash.

    Args:
        msys2_mgr: instance Msys2Manager (optionnel).
        gcc_path: chemin vers arm-none-eabi-gcc (optionnel).

    Returns:
        (cmd, env, shell_prefix) — cmd est la liste d'arguments pour Popen,
        env est le dictionnaire d'environnement, shell_prefix est un
        préfixe à ajouter devant la commande make dans bash (vide sur Linux).

    Raises:
        FileNotFoundError: si MSYS2 n'est pas installé sur Windows.
    """
    import os

    env = os.environ.copy()

    if not is_windows():
        # Linux : make direct, ajout gcc au PATH si besoin
        if gcc_path:
            env["PATH"] = str(gcc_path.parent) + os.pathsep + env.get("PATH", "")
        return ["make"], env, ""

    # Windows : TOUJOURS passer par MSYS2 bash (QMK Makefile requiert un shell Unix)
    mgr = msys2_mgr or Msys2Manager()
    bash = mgr.get_bash_path()
    if not bash:
        raise FileNotFoundError(
            "MSYS2 n'est pas installé. "
            "Les outils de compilation (bash, make) sont nécessaires pour compiler QMK sous Windows."
        )

    # Construire les chemins en format MSYS2 (/c/Users/...)
    msys2_root = bash.parent.parent.parent
    msys2_usr_bin = _win_to_msys2_path(str(msys2_root / "usr" / "bin"))

    # Collecter tous les chemins nécessaires en format MSYS2
    unix_paths = [msys2_usr_bin]
    if gcc_path:
        unix_paths.append(_win_to_msys2_path(str(gcc_path.parent)))

    # Python Windows : dans un venv, python.exe est dans Scripts/
    # Hors venv, python.exe est dans le dossier principal et Scripts/ est un sous-dossier
    python_exe_dir = Path(sys.executable).parent
    unix_paths.append(_win_to_msys2_path(str(python_exe_dir)))
    # Ajouter aussi le dossier Scripts si on n'est pas déjà dedans
    scripts_dir = python_exe_dir / "Scripts"
    if scripts_dir.is_dir():
        unix_paths.append(_win_to_msys2_path(str(scripts_dir)))

    # Construire le préfixe shell qui configure le PATH dans bash
    # IMPORTANT : guillemets doubles pour que $PATH soit expansé par bash
    path_str = ":".join(unix_paths)
    shell_prefix = f'export PATH="{path_str}:$PATH" && '

    # Environnement MSYS2 — MINGW64 requis par le Makefile QMK
    # (MSYS déclenche un warning "not using MINGW64 terminal" qui casse le build)
    env["MSYSTEM"] = "MINGW64"
    env["CHERE_INVOKING"] = "1"

    # Créer un wrapper python3 → python.exe avec chemin absolu
    _ensure_python3_wrapper(msys2_root, _win_to_msys2_path(str(python_exe_dir)))

    return [str(bash), "-lc"], env, shell_prefix


def _ensure_python3_wrapper(msys2_root: Path, python_msys2_dir: str) -> None:
    """Crée un wrapper python3 dans MSYS2/usr/bin/ avec chemin absolu vers python."""
    python3_wrapper = msys2_root / "usr" / "bin" / "python3"
    # Toujours réécrire pour garder le chemin à jour
    try:
        # Utiliser le chemin absolu MSYS2 vers python.exe
        python3_wrapper.write_text(
            f"#!/bin/sh\nexec \"{python_msys2_dir}/python.exe\" \"$@\"\n",
            encoding="utf-8",
        )
        python3_wrapper.chmod(0o755)
        logger.info("Wrapper python3 créé : %s → %s/python.exe", python3_wrapper, python_msys2_dir)
    except OSError:
        logger.warning("Impossible de créer le wrapper python3 dans %s", python3_wrapper)


# ─────────────────────────────────────────────────── Qt components ──


class Msys2InstallWorker(QThread):
    """Thread d'installation MSYS2 avec signaux de progression."""

    progress = Signal(int)
    log_line = Signal(str)
    finished = Signal()
    error = Signal(str)

    def run(self) -> None:
        try:
            Msys2Manager().install(
                progress_callback=self.progress.emit,
                log_callback=self.log_line.emit,
            )
            self.finished.emit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur installation MSYS2")
            self.error.emit(str(exc))


class Msys2SetupDialog(QDialog):
    """Dialogue de progression pour l'installation MSYS2."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("msys2_setup.title"))
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        self._label = QLabel(tr("msys2_setup.downloading"))
        self._label.setObjectName("msys2_setup_label")
        self._progress = QProgressBar()
        self._progress.setObjectName("msys2_setup_progress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)

        self._worker = Msys2InstallWorker()
        self._worker.progress.connect(self._progress.setValue)
        self._worker.log_line.connect(self._label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self) -> None:
        self._label.setText(tr("msys2_setup.ready"))
        self.accept()

    def _on_error(self, msg: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, tr("msys2_setup.error_title"), msg)
        self.reject()
