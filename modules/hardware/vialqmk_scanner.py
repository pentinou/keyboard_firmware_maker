"""vialqmk_scanner — Scan et chargement dynamique des claviers vial-qmk.

Indexe les ~620 claviers du repo vial-qmk cloné qui possèdent un vial.json,
et les charge à la demande en construisant un KeyboardDefinition depuis
keyboard.json + vial.json.

Module pur Python sans dépendance Qt — testable sans QApplication.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from modules.hardware.keyboard_loader import (
    KeyboardDefinition,
    KeyLayout,
    McuOption,
    McuPins,
)
from modules.keyboard_editor.kle_parser import parse_kle_json

logger = logging.getLogger(__name__)

# Mapping processeur QMK → id MCU interne
_PROCESSOR_TO_MCU: dict[str, str] = {
    "RP2040": "rp2040",
    "atmega32u4": "pro_micro",
    "atmega32u2": "pro_micro",
    "at90usb1286": "pro_micro",
    "STM32F072": "stm32f072",
    "STM32F103": "stm32f103",
    "STM32F303": "stm32f303",
    "STM32F401": "stm32f401",
    "STM32F411": "stm32f411",
    "STM32L432": "stm32l432",
    "atmega32a": "atmega32a",
}

# Seuils de catégorie par nombre de touches
CATEGORY_THRESHOLDS: list[tuple[int, str]] = [
    (30, "macropad"),
    (50, "40pct"),
    (68, "60pct"),
    (80, "75pct"),
    (90, "tkl"),
]
CATEGORY_FULLSIZE = "fullsize"
CATEGORY_SPLIT = "split"

CACHE_FILE = Path.home() / ".keyboard_firmware_maker" / "vial-qmk-index.json"


def categorize_keyboard(key_count: int, is_split: bool) -> str:
    """Détermine la catégorie d'un clavier par nombre de touches et type split."""
    if is_split:
        return CATEGORY_SPLIT
    for threshold, cat in CATEGORY_THRESHOLDS:
        if key_count <= threshold:
            return cat
    return CATEGORY_FULLSIZE


def count_keys_from_keymap(keymap: list) -> int:
    """Compte le nombre de touches dans un keymap KLE (liste de listes)."""
    count = 0
    for row in keymap:
        if not isinstance(row, list):
            continue
        for item in row:
            if isinstance(item, str):
                count += 1
    return count


@dataclass
class VialKeyboardEntry:
    """Entrée d'index pour un clavier vial-qmk (métadonnées légères)."""

    name: str               # nom affiché (depuis keyboard.json ou déduit du chemin)
    qmk_path: str           # chemin relatif dans keyboards/ (ex: "crkbd")
    keyboard_dir: Path      # chemin absolu du répertoire clavier
    vial_json_path: Path    # chemin absolu du vial.json
    processor: str = ""     # processeur (ex: "atmega32u4", "RP2040")
    category: str = ""      # catégorie auto-détectée (split, macropad, 40pct, ...)
    key_count: int = 0      # nombre de touches
    is_split: bool = False  # clavier split ?

    @property
    def search_text(self) -> str:
        """Texte combiné pour la recherche (nom + chemin, en minuscules)."""
        return f"{self.name} {self.qmk_path}".lower()


# ── Cache ────────────────────────────────────────────────────────────────────


def _get_git_sha(vial_qmk_dir: Path) -> str:
    """Retourne le SHA HEAD du repo vial-qmk."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=vial_qmk_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _load_cached_index(cache_path: Path, expected_sha: str, keyboards_root: Path) -> list[VialKeyboardEntry] | None:
    """Charge l'index depuis le cache si le SHA correspond."""
    if not cache_path.is_file():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if data.get("git_sha") != expected_sha:
        return None

    entries = []
    for item in data.get("entries", []):
        qmk_path = item["qmk_path"]
        kb_dir = keyboards_root / qmk_path
        # Retrouver le vial.json — chercher dans keymaps/vial/ ou keymaps/default/
        vial_json = kb_dir / "keymaps" / "vial" / "vial.json"
        if not vial_json.is_file():
            vial_json = kb_dir / "keymaps" / "default" / "vial.json"
        entries.append(VialKeyboardEntry(
            name=item["name"],
            qmk_path=qmk_path,
            keyboard_dir=kb_dir,
            vial_json_path=vial_json,
            processor=item.get("processor", ""),
            category=item.get("category", ""),
            key_count=item.get("key_count", 0),
            is_split=item.get("is_split", False),
        ))
    logger.info("vial-qmk : %d claviers chargés depuis le cache", len(entries))
    return entries


def _save_cached_index(cache_path: Path, sha: str, entries: list[VialKeyboardEntry]) -> None:
    """Sauvegarde l'index dans le cache JSON."""
    data = {
        "git_sha": sha,
        "entries": [
            {
                "name": e.name,
                "qmk_path": e.qmk_path,
                "processor": e.processor,
                "category": e.category,
                "key_count": e.key_count,
                "is_split": e.is_split,
            }
            for e in entries
        ],
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data), encoding="utf-8")
        logger.info("vial-qmk : cache sauvegardé (%d entrées)", len(entries))
    except OSError as exc:
        logger.warning("Impossible de sauvegarder le cache vial-qmk : %s", exc)


# ── Scan ─────────────────────────────────────────────────────────────────────


def scan_vial_keyboards(vial_qmk_dir: Path) -> list[VialKeyboardEntry]:
    """Scanne le repo vial-qmk et retourne un index de tous les claviers avec vial.json.

    Utilise un cache JSON invalidé par le SHA HEAD du repo git.
    """
    keyboards_root = vial_qmk_dir / "keyboards"
    if not keyboards_root.is_dir():
        logger.warning("Répertoire vial-qmk/keyboards introuvable : %s", keyboards_root)
        return []

    # Vérifier le cache
    sha = _get_git_sha(vial_qmk_dir)
    if sha:
        cached = _load_cached_index(CACHE_FILE, sha, keyboards_root)
        if cached is not None:
            return cached

    entries: list[VialKeyboardEntry] = []

    for vial_json in keyboards_root.rglob("vial.json"):
        # Pattern attendu : keyboards/{path}/keymaps/{vial|default}/vial.json
        keymap_dir = vial_json.parent          # keymaps/vial/
        keymaps_dir = keymap_dir.parent        # keymaps/
        if keymaps_dir.name != "keymaps":
            continue
        kb_dir = keymaps_dir.parent            # le répertoire clavier

        qmk_path = str(kb_dir.relative_to(keyboards_root))

        # Charger le nom et processeur depuis keyboard.json (fusion hiérarchique)
        name = qmk_path.replace("/", " / ").title()
        processor = ""
        is_split = False

        data = _merge_keyboard_data(kb_dir, keyboards_root)
        if data:
            name = data.get("keyboard_name", name)
            processor = data.get("processor", "")
            split_config = data.get("split", {})
            if isinstance(split_config, dict):
                is_split = bool(split_config.get("enabled", False))

        # Compter les touches depuis vial.json
        key_count = 0
        try:
            vial_data = json.loads(vial_json.read_text(encoding="utf-8"))
            keymap = vial_data.get("layouts", {}).get("keymap", [])
            key_count = count_keys_from_keymap(keymap)
        except (json.JSONDecodeError, OSError):
            pass

        category = categorize_keyboard(key_count, is_split)

        entries.append(VialKeyboardEntry(
            name=name,
            qmk_path=qmk_path,
            keyboard_dir=kb_dir,
            vial_json_path=vial_json,
            processor=processor,
            category=category,
            key_count=key_count,
            is_split=is_split,
        ))

    entries.sort(key=lambda e: e.name.lower())
    logger.info("vial-qmk : %d claviers indexés", len(entries))

    # Sauvegarder le cache
    if sha:
        _save_cached_index(CACHE_FILE, sha, entries)

    return entries


def _find_all_keyboard_jsons(kb_dir: Path, root: Path) -> list[Path]:
    """Trouve tous les keyboard.json et info.json pertinents pour un clavier.

    QMK fusionne hiérarchiquement les données : info.json du parent,
    puis keyboard.json du parent, puis ceux des sous-répertoires (revisions).
    On retourne tous les fichiers trouvés, ordonnés du plus général au plus spécifique.
    """
    files: list[Path] = []

    # 1. Fichiers dans le répertoire clavier lui-même (les plus généraux)
    if (kb_dir / "info.json").is_file():
        files.append(kb_dir / "info.json")
    if (kb_dir / "keyboard.json").is_file():
        files.append(kb_dir / "keyboard.json")

    # 2. Sous-répertoires (revisions) — les plus spécifiques
    for sub in sorted(kb_dir.rglob("keyboard.json"), key=lambda p: len(p.parts)):
        if sub not in files:
            files.append(sub)
    for sub in sorted(kb_dir.rglob("info.json"), key=lambda p: len(p.parts)):
        if sub not in files and sub != kb_dir / "info.json":
            files.append(sub)

    return files


def _merge_keyboard_data(kb_dir: Path, root: Path) -> dict:
    """Fusionne toutes les données keyboard.json/info.json comme le fait QMK."""
    files = _find_all_keyboard_jsons(kb_dir, root)
    merged: dict = {}
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            _deep_merge(merged, data)
        except (json.JSONDecodeError, OSError):
            continue
    return merged


def _deep_merge(base: dict, override: dict) -> None:
    """Fusionne override dans base récursivement (in-place)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _build_layout_from_vial(vial_json_path: Path, is_split: bool) -> dict:
    """Parse le keymap KLE du vial.json en layout dict de KeyLayout.

    Pour les splits, les touches sont réparties gauche/droite par position x.
    Pour les non-splits, toutes les touches vont dans 'keys'.
    """
    try:
        vial_data = json.loads(vial_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    keymap_raw = vial_data.get("layouts", {}).get("keymap", [])
    if not keymap_raw:
        return {}

    result = parse_kle_json(json.dumps(keymap_raw))
    if not result.keys:
        return {}

    def _to_key_layout(k) -> KeyLayout:
        return KeyLayout(
            row=max(k.row, 0), col=max(k.col, 0),
            x=k.x, y=k.y,
            w=k.w, h=k.h,
            r=k.r,
            encoder=k.encoder,
        )

    all_keys = [_to_key_layout(k) for k in result.keys]

    if is_split and all_keys:
        max_x = max(k.x + k.w for k in all_keys)
        mid = max_x / 2
        left = [k for k in all_keys if k.x + k.w / 2 < mid]
        right = [k for k in all_keys if k.x + k.w / 2 >= mid]
        return {"left": left, "right": right, "keys": []}

    return {"left": [], "right": [], "keys": all_keys}


def load_vial_keyboard(entry: VialKeyboardEntry) -> KeyboardDefinition:
    """Charge un KeyboardDefinition complet depuis un VialKeyboardEntry."""
    kb_dir = entry.keyboard_dir

    # Charger et fusionner tous les keyboard.json/info.json
    keyboards_root = kb_dir.parent
    while keyboards_root.name != "keyboards" and keyboards_root != keyboards_root.parent:
        keyboards_root = keyboards_root.parent
    kb_data = _merge_keyboard_data(kb_dir, keyboards_root)

    # Extraire les infos hardware
    processor = kb_data.get("processor", entry.processor)
    bootloader = kb_data.get("bootloader", "")
    diode_direction = kb_data.get("diode_direction", "COL2ROW")
    features = kb_data.get("features", {})

    # Matrix pins
    matrix_pins = kb_data.get("matrix_pins", {})
    pin_rows = matrix_pins.get("rows", [])
    pin_cols = matrix_pins.get("cols", [])

    # Split detection
    split_config = kb_data.get("split", {})
    is_split = bool(split_config.get("enabled", False)) if isinstance(split_config, dict) else False

    # Serial pin for split
    serial_tx = ""
    if is_split and isinstance(split_config, dict):
        serial = split_config.get("serial", {})
        if isinstance(serial, dict):
            serial_tx = serial.get("pin", "")

    # WS2812 pin
    ws2812_pin = ""
    ws2812_config = kb_data.get("ws2812", {})
    if isinstance(ws2812_config, dict):
        ws2812_pin = ws2812_config.get("pin", "")

    # Encoder pins
    encoder_a: list[str] = []
    encoder_b: list[str] = []
    encoders = kb_data.get("encoder", {})
    if isinstance(encoders, dict):
        rotary = encoders.get("rotary", [])
        if isinstance(rotary, list):
            for enc in rotary:
                if isinstance(enc, dict):
                    if "pin_a" in enc:
                        encoder_a.append(enc["pin_a"])
                    if "pin_b" in enc:
                        encoder_b.append(enc["pin_b"])

    # Capabilities
    has_oled = bool(features.get("oled", False))
    has_rgb = bool(features.get("rgblight", False)) or bool(features.get("rgb_matrix", False))
    has_encoder = bool(features.get("encoder", False))

    # Matrix size from keyboard.json layouts or vial.json
    matrix_rows = len(pin_rows) * (2 if is_split else 1) if pin_rows else 0
    matrix_cols = len(pin_cols) if pin_cols else 0

    # If no matrix from pins, try vial.json matrix field
    if not matrix_rows or not matrix_cols:
        try:
            vial_data = json.loads(entry.vial_json_path.read_text(encoding="utf-8"))
            vial_matrix = vial_data.get("matrix", {})
            matrix_rows = matrix_rows or vial_matrix.get("rows", 0)
            matrix_cols = matrix_cols or vial_matrix.get("cols", 0)
        except (json.JSONDecodeError, OSError):
            pass

    # Build MCU option
    mcu_id = _PROCESSOR_TO_MCU.get(processor, processor.lower() or "unknown")
    mcu = McuOption(
        id=mcu_id,
        display_name=processor or "Unknown",
        description=f"Auto-detected from vial-qmk ({entry.qmk_path})",
        bootloader=bootloader,
        pins=McuPins(
            matrix_rows=pin_rows,
            matrix_cols=pin_cols,
            serial_tx=serial_tx,
            ws2812=ws2812_pin,
            encoder_a=encoder_a,
            encoder_b=encoder_b,
        ),
    )

    # Construire le layout physique depuis le keymap KLE du vial.json
    layout = _build_layout_from_vial(entry.vial_json_path, is_split)

    return KeyboardDefinition(
        model=entry.qmk_path.replace("/", "-"),
        display_name=entry.name,
        description=f"Importé depuis vial-qmk ({entry.qmk_path})",
        mcu_options=[mcu],
        capabilities={"oled": has_oled, "rgb": has_rgb},
        matrix={"rows": max(matrix_rows, 1), "cols": max(matrix_cols, 1)},
        layout=layout,
        vial_name=entry.name,
        diode_direction=diode_direction,
        layout_macro="LAYOUT",
        has_encoder=has_encoder,
        split=is_split,
        vial_qmk_keyboard=entry.qmk_path,
    )
