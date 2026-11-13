"""Serveur HTTP de l'interface web : sert web/static/ et une API JSON.

Même principe qu'IA Launcher : bibliothèque standard (ThreadingHTTPServer), pas
d'authentification (écoute sur 127.0.0.1 par défaut ; derrière YunoHost, c'est le
SSO qui protège l'accès).

Le serveur ne garde aucun projet : le projet vit dans le navigateur, qui l'envoie
avec chaque demande (compilation, import de keymap). Seuls les images OLED
envoyées et les firmwares compilés sont stockés, sous ~/.keyboard_firmware_maker/web/.
"""
from __future__ import annotations

import base64
import dataclasses
import hashlib
import io
import json
import mimetypes
import re
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from _version import __version__
from config import CUSTOM_KEYBOARDS_DIR, KEYBOARDS_DIR
from models.project_model import ProjectModel
from web import jobs

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY = 20 * 1024 * 1024   # images OLED et projets : largement suffisant
_ACTIVITE = {"derniere": time.time()}


# ─────────────────────────────────────────────────────────── données ──

def keyboards() -> list[dict]:
    """Définitions des claviers (prédéfinis + personnalisés), sans le brochage."""
    from modules.hardware.keyboard_loader import load_all_keyboards

    result = []
    for kb in load_all_keyboards(KEYBOARDS_DIR, CUSTOM_KEYBOARDS_DIR):
        data = dataclasses.asdict(kb)
        for mcu in data["mcu_options"]:
            del mcu["pins"]
        del data["default_keymap_zmk"]
        result.append(data)
    return result


def effects() -> dict:
    from modules.rgb_editor.effects import EFFECT_TYPES, NEEDS_FRAMEBUFFER

    return {
        "types": [
            {"id": e.id, "name": e.name, "description": e.description, "category": e.category}
            for e in EFFECT_TYPES
            # non compilés par le générateur (RGB_MATRIX_FRAMEBUFFER_EFFECTS absent)
            if e.id not in NEEDS_FRAMEBUFFER
        ],
    }


def strings(lang: str) -> dict[str, str]:
    """Textes de l'application de bureau (libellés et infobulles), réutilisés par l'interface."""
    from i18n.translations import STRINGS

    return {**STRINGS["fr"], **STRINGS.get(lang, {})}


def status() -> dict:
    """État des outils de compilation."""
    from modules.build_manager.toolchain import detect_toolchain
    from modules.build_manager.zmk_builder import is_west_available, is_zephyr_sdk_installed

    toolchain = detect_toolchain()
    job = jobs.running()
    return {
        "qmk": {"vial_qmk": jobs.vial_qmk_ready(), "gcc": toolchain.is_available,
                "gcc_version": toolchain.version, "gcc_source": toolchain.source},
        "zmk": {"sdk": is_zephyr_sdk_installed(), "west": is_west_available()},
        "running": job.id if job else None,
    }


def full_project(model: ProjectModel) -> dict:
    """Le projet avec TOUS ses champs (to_dict() omet les listes vides et les valeurs par défaut,
    l'interface en a besoin). Mêmes noms de clés que to_dict() : le fichier reste lisible par
    l'application de bureau. Les frames d'images, calculées à la compilation, sont retirées."""
    data = dataclasses.asdict(model)
    for side in ("left", "right"):
        for img in data["oled"][side]["images"]:
            img.pop("frames", None)
            img.pop("delays", None)
    return data


def normalize_project(data: dict) -> dict:
    """Projet complété par les valeurs par défaut du modèle (ouverture d'un fichier, nouveau projet)."""
    return full_project(ProjectModel.from_dict(data))


def import_keymap(filename: str, content: str, firmware: str) -> dict:
    """Même traitement que l'import des Options avancées de l'application de bureau."""
    from modules.keymap_importer.common import FORMAT_UNKNOWN, FORMAT_VIAL, ConversionReport, detect_format
    from modules.keymap_importer.zmk_to_qmk import convert_zmk_layers_to_qmk, parse_zmk_keymap

    fmt = detect_format(Path(filename), content)
    if fmt == FORMAT_UNKNOWN:
        raise ValueError("format de keymap non reconnu (attendu : .vil / .json Vial, ou .keymap ZMK)")
    report = ConversionReport()
    if fmt == FORMAT_VIAL:
        keymap = json.loads(content)
    else:
        layers = parse_zmk_keymap(content)
        if not layers:
            raise ValueError("aucune couche trouvée dans ce keymap ZMK")
        if firmware == "qmk":
            _, report = convert_zmk_layers_to_qmk(layers)
        keymap = {"zmk_layers": layers}
    return {
        "format": fmt,
        "keymap": keymap,
        "cross_format": (fmt == FORMAT_VIAL) != (firmware == "qmk"),
        "report": {"converted": report.converted, "warnings": report.warnings,
                   "dropped": [dataclasses.asdict(d) for d in report.dropped]},
    }


def save_image(name: str, data: bytes) -> dict:
    """Enregistre une image OLED envoyée par le navigateur et renvoie son aperçu converti."""
    suffix = Path(name).suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
        raise ValueError("format d'image non pris en charge (png, jpg, gif, bmp, webp)")
    jobs.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(name).stem)[:40] or "image"
    path = jobs.UPLOADS_DIR / f"{hashlib.sha256(data).hexdigest()[:12]}_{stem}{suffix}"
    path.write_bytes(data)
    try:
        return image_info(str(path))
    except Exception:
        path.unlink(missing_ok=True)
        raise ValueError("fichier image illisible") from None


def image_info(image_path: str) -> dict:
    """Aperçu (1re frame convertie 1 bit, PNG en data-URL) d'une image déjà envoyée."""
    from PIL import Image

    from modules.oled_editor.processor import OLED_HEIGHT, OLED_WIDTH, convert_image_natural

    path = Path(image_path).resolve()
    if jobs.UPLOADS_DIR.resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError("image absente du serveur : renvoyez-la depuis l'onglet OLED")
    frames, _delays, natural_w, natural_h = convert_image_natural(path)
    # La frame est un canevas 32×128 où l'image est centrée : on ne garde que sa zone utile.
    canvas = Image.frombytes("L", (OLED_WIDTH, OLED_HEIGHT), frames[0])
    left, top = (OLED_WIDTH - natural_w) // 2, (OLED_HEIGHT - natural_h) // 2
    buf = io.BytesIO()
    canvas.crop((left, top, left + natural_w, top + natural_h)).save(buf, "PNG")
    return {
        "image_path": str(path), "natural_w": natural_w, "natural_h": natural_h, "frames": len(frames),
        "preview": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
    }


# ─────────────────────────────────────────────────────────── HTTP ──

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    allow: frozenset[str] = frozenset()   # vide = tout le monde (cf. serve(allow=…))

    def log_message(self, fmt, *args):  # silence
        pass

    def handle_one_request(self):
        # Filtrage des adresses : seul le portail (qui a la connexion SSO) doit pouvoir entrer.
        if self.allow and self.client_address[0] not in self.allow:
            self.close_connection = True
            return
        super().handle_one_request()

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, "application/json; charset=utf-8", data)

    def _send(self, code, ctype, data, extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for key, value in extra:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _raw_body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("requête trop volumineuse")
        return self.rfile.read(n)

    def _file(self, root: Path, rel: str, download: bool = False):
        root = root.resolve()
        p = (root / rel).resolve()
        if root not in p.parents or not p.is_file():
            self.send_error(404)
            return
        extra = [("Content-Disposition", f"attachment; filename*=UTF-8''{quote(p.name)}")] if download else []
        ctype = "application/octet-stream" if download else (mimetypes.guess_type(str(p))[0] or "application/octet-stream")
        self._send(200, ctype, p.read_bytes(), extra)

    def _dispatch(self, handler):
        """Erreurs de saisie → 400, le reste → 500 ; toujours en JSON pour l'interface."""
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path != "/api/activity":
            _ACTIVITE["derniere"] = time.time()
        try:
            handler(u.path, q)
        except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, 400)
        except RuntimeError as exc:
            self._json({"error": str(exc)}, 409)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._json({"error": str(exc)}, 500)

    def do_GET(self):
        self._dispatch(self._get)

    def do_POST(self):
        self._dispatch(self._post)

    def _get(self, path, q):
        if path == "/":
            return self._file(STATIC_DIR, "index.html")
        if path.startswith("/static/"):
            return self._file(STATIC_DIR, path[len("/static/"):])
        if path == "/api/meta":
            return self._json({"version": __version__, "keyboards": keyboards(), "effects": effects(),
                               "strings": strings(q.get("lang", "fr")),
                               "default_project": full_project(ProjectModel())})
        if path == "/api/status":
            return self._json(status())
        if path == "/api/activity":
            # pour un portier « à la demande » (ondemand.py d'IA Launcher) : ne pas arrêter pendant un build
            job = jobs.running()
            return self._json({"derniere_requete": _ACTIVITE["derniere"],
                               "taches": [job.label] if job else [], "occupe": bool(job)})
        if path == "/api/oled/image":
            return self._json(image_info(q["path"]))
        m = re.fullmatch(r"/api/jobs/(\w+)", path)
        if m:
            job = jobs.get(m.group(1))
            if not job:
                return self._json({"error": "tâche inconnue (le serveur a peut-être redémarré)"}, 404)
            return self._json(job.to_dict(int(q.get("since", 0))))
        m = re.fullmatch(r"/api/jobs/(\w+)/files/([^/]+)", path)
        if m:
            return self._file(jobs.JOBS_DIR / m.group(1), m.group(2), download=True)
        self.send_error(404)

    def _post(self, path, q):
        if path == "/api/oled/image":   # corps binaire : le fichier image
            return self._json(save_image(q.get("name", "image.png"), self._raw_body()))
        body = json.loads(self._raw_body() or b"{}")
        if path == "/api/project/normalize":
            return self._json({"project": normalize_project(body["project"])})
        if path == "/api/keymap/import":
            return self._json(import_keymap(body["filename"], body["content"], body.get("firmware", "qmk")))
        if path == "/api/build":
            return self._json({"job": jobs.start_build(ProjectModel.from_dict(body["project"])).to_dict()})
        if path == "/api/setup/vial-qmk":
            return self._json({"job": jobs.start_vial_qmk_setup().to_dict()})
        m = re.fullmatch(r"/api/jobs/(\w+)/cancel", path)
        if m:
            job = jobs.get(m.group(1))
            if job and job.state == "running":
                job.cancel()
            return self._json({"ok": bool(job)})
        self.send_error(404)


def _open_browser(url: str) -> None:
    """Sous WSL, xdg-open ne connaît pas le navigateur Windows : passer par cmd.exe."""
    import os
    import shutil
    import subprocess
    import webbrowser

    if "microsoft" in os.uname().release.lower() and shutil.which("cmd.exe"):
        subprocess.Popen(["cmd.exe", "/c", "start", "", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    webbrowser.open(url)


def serve(port: int = 8767, open_browser: bool = True, host: str = "127.0.0.1", allow: list[str] | None = None) -> None:
    if allow:
        Handler.allow = frozenset({"127.0.0.1", "::1", *allow})
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{port}"
    print(f"Keyboard Firmware Maker (web) : {url}   (Ctrl+C pour quitter)", flush=True)
    if allow:
        print(f"adresses acceptées : {', '.join(sorted(Handler.allow))}", flush=True)
    elif host != "127.0.0.1":
        print(f"⚠ écoute sur {host} : pas d'authentification ; limitez l'accès à ce port (pare-feu) "
              "au seul proxy qui en a une, ex. le SSO YunoHost", flush=True)
    if open_browser:
        threading.Timer(0.8, lambda: _open_browser(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        job = jobs.running()
        if job:
            job.cancel()
