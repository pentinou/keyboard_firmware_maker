"""Tâches longues de l'interface web : compilation QMK / ZMK et téléchargement de Vial-QMK.

Les compilations réutilisent tels quels les workers de l'application de bureau
(`BuildWorker`, `ZmkBuildWorker`). Ce sont des QThread, mais ils n'ont besoin ni
d'une QApplication ni d'une boucle d'événements : leurs signaux sont reliés en
connexion directe, donc reçus dans le thread du worker.

Une seule tâche à la fois : les builds partagent le dossier vial-qmk et le
workspace ZMK.
"""
from __future__ import annotations

import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from config import CACHE_DIR, CUSTOM_KEYBOARDS_DIR, KEYBOARDS_DIR, VIAL_QMK_DIR
from models.project_model import ProjectModel
from modules.hardware.keyboard_loader import get_firmware_type, load_keyboard

WEB_DIR = CACHE_DIR / "web"
JOBS_DIR = WEB_DIR / "jobs"
UPLOADS_DIR = WEB_DIR / "uploads"

_KEEP_JOBS = 10
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LOCK = threading.Lock()
_JOBS: dict[str, "Job"] = {}


class Job:
    """Une tâche et son journal, consultés par l'interface à intervalle régulier."""

    def __init__(self, kind: str, label: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind            # "build" | "setup"
        self.label = label
        self.state = "running"      # "running" | "done" | "error"
        self.progress = 0
        self.log: list[str] = []
        self.error = ""
        self.files: list[Path] = []
        self.info: dict = {}
        self.created = time.time()
        self.cancel = lambda: None

    def add_log(self, line: str) -> None:
        self.log.append(_ANSI.sub("", line))   # make colore ses [OK] / [WARNINGS]

    def to_dict(self, since: int = 0) -> dict:
        return {
            "id": self.id, "kind": self.kind, "label": self.label, "state": self.state,
            "progress": self.progress, "error": self.error, "info": self.info,
            "log": self.log[since:], "log_next": len(self.log),
            "files": [{"name": f.name, "size": f.stat().st_size} for f in self.files if f.is_file()],
        }


def get(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def running() -> Job | None:
    return next((j for j in _JOBS.values() if j.state == "running"), None)


def _register(job: Job) -> None:
    """Enregistre la tâche et oublie les plus anciennes (fichiers compris)."""
    _JOBS[job.id] = job
    finished = sorted((j for j in _JOBS.values() if j.state != "running"), key=lambda j: j.created)
    for old in finished[:-_KEEP_JOBS]:
        shutil.rmtree(JOBS_DIR / old.id, ignore_errors=True)
        del _JOBS[old.id]


def firmware_of(model: ProjectModel) -> str:
    """'qmk' ou 'zmk' selon le MCU choisi dans le projet (clavier et MCU doivent exister)."""
    name = model.keyboard.model
    # le nom sert à construire des chemins (YAML, shield ZMK) : pas de « ../ »
    if re.fullmatch(r"[A-Za-z0-9_-]+", name or ""):
        for folder in (KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR):
            path = folder / f"{name}.yaml"
            if path.is_file():
                kb_def = load_keyboard(path)
                if not any(opt.id == model.keyboard.mcu for opt in kb_def.mcu_options):
                    raise ValueError(f"microcontrôleur inconnu pour {name} : {model.keyboard.mcu or '(aucun)'}")
                return get_firmware_type(kb_def, model.keyboard.mcu)
    raise ValueError(f"clavier inconnu : {name or '(aucun)'}")


def load_image_frames(model: ProjectModel, log=lambda _line: None) -> None:
    """Reconvertit les images OLED du projet (les frames ne sont pas enregistrées dans le projet).

    Seules les images envoyées par l'interface (dossier des envois) sont lues :
    un projet ne doit pas faire ouvrir au serveur un fichier arbitraire.
    """
    from modules.oled_editor.processor import convert_image_natural

    uploads = UPLOADS_DIR.resolve()
    for side in (model.oled.left, model.oled.right):
        for img in side.images:
            path = Path(img.image_path).resolve() if img.image_path else None
            if path is None or uploads not in path.parents or not path.is_file():
                log(f"[WARN] Image OLED ignorée (à renvoyer depuis l'onglet OLED) : {img.image_path}")
                continue
            img.frames, img.delays, img.natural_w, img.natural_h = convert_image_natural(path)


def start_build(model: ProjectModel) -> Job:
    """Lance la compilation du projet. Lève RuntimeError si une tâche est déjà en cours."""
    from PySide6.QtCore import Qt

    direct = Qt.ConnectionType.DirectConnection
    firmware = firmware_of(model)

    with _LOCK:
        if running():
            raise RuntimeError("une compilation est déjà en cours")
        job = Job("build", f"Compilation {firmware.upper()} — {model.keyboard.model}")
        job.info = {"firmware": firmware, "model": model.keyboard.model, "mcu": model.keyboard.mcu,
                    "variant": model.keyboard.layout_variant}
        _register(job)

    def fail(message: str) -> None:
        job.error, job.state = message, "error"

    try:
        load_image_frames(model, job.add_log)
        if firmware == "zmk":
            from modules.build_manager.zmk_builder import ZmkBuildWorker

            worker = ZmkBuildWorker(model=model)
            worker.success.connect(lambda paths: _finish(job, [Path(p) for p in paths], zmk=True), direct)
        else:
            from modules.build_manager.builder import MCU_FLASH, BuildWorker
            from modules.build_manager.toolchain import INSTALL_GUIDE_MSG, detect_toolchain

            if not vial_qmk_ready():
                return _fail_now(job, "Vial-QMK n'est pas encore téléchargé : lancez son installation depuis l'onglet Build.")
            toolchain = detect_toolchain()
            if not toolchain.is_available:
                return _fail_now(job, INSTALL_GUIDE_MSG)
            job.info["flash_bytes"] = MCU_FLASH.get(model.keyboard.mcu, 0)
            worker = BuildWorker(model=model, vial_qmk_dir=VIAL_QMK_DIR, gcc_path=toolchain.gcc_path)
            worker.success.connect(lambda path: _finish(job, [Path(path)], zmk=False), direct)
    except Exception as exc:  # noqa: BLE001 — la tâche doit toujours se terminer
        return _fail_now(job, str(exc))

    worker.progress.connect(lambda pct: setattr(job, "progress", pct), direct)
    worker.log_line.connect(job.add_log, direct)
    worker.error.connect(fail, direct)
    job.cancel = worker.stop

    def run() -> None:
        worker.start()
        worker.wait()
        if job.state == "running":   # worker terminé sans succès ni erreur signalée
            fail("La compilation s'est arrêtée sans produire de firmware. Consultez le journal.")

    threading.Thread(target=run, daemon=True).start()
    return job


def _fail_now(job: Job, message: str) -> Job:
    job.error, job.state = message, "error"
    return job


def _finish(job: Job, uf2_paths: list[Path], zmk: bool) -> None:
    """Copie les .uf2 sous leur nom d'export (le même que l'application de bureau)."""
    dest_dir = JOBS_DIR / job.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    model = job.info.get("model") or "firmware"
    for uf2 in uf2_paths:
        if not uf2.is_file():
            continue
        # ZMK : chaque moitié s'appelle zmk.uf2, c'est le dossier de build qui les distingue
        tag = uf2.parent.parent.name if zmk else job.info.get("variant")
        name = f"KFM_{model}_{tag}.uf2" if tag else f"KFM_{model}.uf2"
        shutil.copy2(uf2, dest_dir / name)
        job.files.append(dest_dir / name)
    if job.files:
        job.progress, job.state = 100, "done"
    else:
        job.error, job.state = "Aucun fichier .uf2 produit.", "error"


def vial_qmk_ready() -> bool:
    """Même contrôle que VialQmkManager.is_ready(), sans importer QtWidgets."""
    return (VIAL_QMK_DIR / "Makefile").is_file() and (VIAL_QMK_DIR / "lib" / "chibios" / "os").is_dir()


def start_vial_qmk_setup() -> Job:
    """Télécharge Vial-QMK et ses sous-modules (nécessaire avant le premier build QMK)."""
    from modules.build_manager.vial_qmk_manager import VialQmkManager

    with _LOCK:
        if running():
            raise RuntimeError("une tâche est déjà en cours")
        job = Job("setup", "Téléchargement de Vial-QMK")
        _register(job)

    def run() -> None:
        try:
            VialQmkManager().download(
                progress_callback=lambda pct: setattr(job, "progress", pct),
                log_callback=job.add_log,
            )
            job.progress, job.state = 100, "done"
        except Exception as exc:  # noqa: BLE001
            job.error, job.state = str(exc), "error"

    threading.Thread(target=run, daemon=True).start()
    return job
