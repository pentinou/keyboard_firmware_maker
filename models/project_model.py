"""ProjectModel — état central sérialisable de l'application.

Ce dataclass porte toute la configuration utilisateur (clavier, OLED, RGB, build).
Il est passé par injection de dépendance à chaque widget (jamais en singleton global).
Format JSON : clés snake_case, couleurs hex #RRGGBB, chemins absolus.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class KeyboardConfig:
    """Configuration du matériel sélectionné."""

    model: str = ""
    mcu: str = ""
    oled_sides: list[str] = field(default_factory=list)
    # [] = aucun  |  ["left"] | ["right"] | ["left","right"]
    layout_variant: str = ""
    # slug de la variante sélectionnée, "" = première variante (ou pas de variante)
    rgb_enabled: bool = False
    # override de la capability RGB YAML — choix de build de l'utilisateur
    rgb_underglow_per_side: int = -1
    # -1 = auto (toutes les LEDs underglow de la config native)
    #  0 = aucune LED underglow/accent sur le PCB
    #  N = exactement N LEDs underglow/accent par moitié (split) ou total (non-split)
    zmk_studio_transport: str = "ble"
    # Transport ZMK Studio : "ble" (sans fil, défaut) ou "usb" (CDC ACM filaire).
    # Affecte uniquement les firmwares ZMK. Ignoré pour QMK.
    debug_logging: bool = False
    # Si True, active le logging Zephyr/ZMK sur USB CDC ACM (port série virtuel).
    # Permet de capturer les messages de boot (panic, k_oops, init OLED/BLE/USB,
    # etc.) via `screen /dev/ttyACM0 115200` ou `picocom`. ZMK uniquement.
    use_custom_keymap: bool = False
    # Si True (ZMK uniquement) : utilise `custom_keymap` au lieu du default
    # défini dans le YAML du clavier. Le format est celui du converter Vial-ZMK.
    custom_keymap: dict[str, Any] | None = None
    # Contenu brut du keymap Vial-QMK importé (JSON). Converti à la volée par
    # `modules.keymap_importer.vial_to_zmk.convert_vial_to_zmk_keymap` au moment
    # de la génération du firmware. None si aucun import effectué.

    def to_dict(self) -> dict[str, Any]:
        d = {
            "model": self.model,
            "mcu": self.mcu,
            "oled_sides": list(self.oled_sides),
            "layout_variant": self.layout_variant,
            "rgb_enabled": self.rgb_enabled,
        }
        if self.rgb_underglow_per_side != -1:
            d["rgb_underglow_per_side"] = self.rgb_underglow_per_side
        if self.zmk_studio_transport != "ble":
            d["zmk_studio_transport"] = self.zmk_studio_transport
        if self.debug_logging:
            d["debug_logging"] = True
        if self.use_custom_keymap:
            d["use_custom_keymap"] = True
        if self.custom_keymap is not None:
            d["custom_keymap"] = self.custom_keymap
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeyboardConfig":
        # Migration: old bool rgb_underglow → new int rgb_underglow_per_side
        if "rgb_underglow_per_side" in data:
            try:
                underglow = int(data["rgb_underglow_per_side"])
            except (ValueError, TypeError):
                underglow = -1
        elif "rgb_underglow" in data:
            underglow = -1 if data["rgb_underglow"] else 0
        else:
            underglow = -1
        transport = str(data.get("zmk_studio_transport", "ble")).lower()
        if transport not in ("ble", "usb"):
            transport = "ble"
        return cls(
            model=data.get("model", ""),
            mcu=data.get("mcu", ""),
            oled_sides=list(data.get("oled_sides", [])),
            layout_variant=data.get("layout_variant", ""),
            rgb_enabled=bool(data.get("rgb_enabled", False)),
            rgb_underglow_per_side=underglow,
            zmk_studio_transport=transport,
            debug_logging=bool(data.get("debug_logging", False)),
            use_custom_keymap=bool(data.get("use_custom_keymap", False)),
            custom_keymap=data.get("custom_keymap"),
        )


@dataclass
class ZmkBatteryWidget:
    """Widget ZMK natif batterie pour status_screen custom.

    `show_peer` : si True, affiche le niveau de la moitié peer (split-battery
    central uniquement, requiert `CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y`).
    Sinon affiche la batterie locale.
    """

    enabled: bool = False
    col: int = 0
    line: int = 0
    show_peer: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "col": self.col,
            "line": self.line,
            "show_peer": self.show_peer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ZmkBatteryWidget":
        try:
            col = int(data.get("col", 0))
        except (ValueError, TypeError):
            col = 0
        try:
            line = int(data.get("line", 0))
        except (ValueError, TypeError):
            line = 0
        return cls(
            enabled=bool(data.get("enabled", False)),
            col=col, line=line,
            show_peer=bool(data.get("show_peer", False)),
        )


@dataclass
class OledOverlayItem:
    """Position d'un overlay (layer, caps lock, WPM) sur l'écran OLED.

    col  : colonne curseur QMK (0–4 pour OLED 32px avec font 6px)
    line : page QMK (0–15 pour OLED 128px / 8)
    """

    enabled: bool = False
    col: int = 0
    line: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "col": self.col, "line": self.line}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledOverlayItem":
        try:
            col = int(data.get("col", 0))
        except (ValueError, TypeError):
            col = 0
        try:
            line = int(data.get("line", 0))
        except (ValueError, TypeError):
            line = 0
        return cls(
            enabled=bool(data.get("enabled", False)),
            col=col,
            line=line,
        )


@dataclass
class OledImageItem:
    """Une image importée sur l'écran OLED avec position et options.

    Note: `frames` est uniquement runtime (données binaires converties).
    Il n'est PAS inclus dans la sérialisation JSON.
    natural_w / natural_h : dimensions du thumbnail OLED en pixels (avant padding).
    """

    image_path: str = ""
    frames: list[bytes] = field(default_factory=list, repr=False)  # runtime only
    delays: list[int] = field(default_factory=list, repr=False)    # runtime only (ms par frame)
    natural_w: int = 32   # largeur thumbnail (pixels OLED)
    natural_h: int = 128  # hauteur thumbnail (pixels OLED)
    col: int = 0          # colonne curseur QMK (0-4)
    line: int = 0         # page QMK (0-15)
    inverted: bool = False
    # Phase 4 OLED ZMK custom : couche keymap où l'image est visible.
    # -1 = toutes les couches (image "globale", toujours présente).
    # 0/1/2/... = uniquement quand cette couche est la plus haute active.
    layer: int = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_path": self.image_path,
            "natural_w": self.natural_w,
            "natural_h": self.natural_h,
            "col": self.col,
            "line": self.line,
            "inverted": self.inverted,
            "layer": self.layer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledImageItem":
        def _int(key: str, default: int) -> int:
            try:
                return int(data.get(key, default))
            except (ValueError, TypeError):
                return default
        return cls(
            image_path=data.get("image_path", ""),
            natural_w=_int("natural_w", 32),
            natural_h=_int("natural_h", 128),
            col=_int("col", 0),
            line=_int("line", 0),
            inverted=bool(data.get("inverted", False)),
            layer=_int("layer", -1),
        )


@dataclass
class OledSideConfig:
    """Configuration OLED d'une moitié du clavier split.

    Note: OledImageItem.frames est uniquement runtime (données binaires converties).
    """

    images: list[OledImageItem] = field(default_factory=list)
    layer: OledOverlayItem = field(default_factory=OledOverlayItem)
    caps_lock: OledOverlayItem = field(default_factory=OledOverlayItem)
    wpm: OledOverlayItem = field(default_factory=OledOverlayItem)
    rgb_mode: OledOverlayItem = field(default_factory=OledOverlayItem)
    kfm: OledOverlayItem = field(default_factory=OledOverlayItem)
    katawajojo_enabled: bool = False
    katawajojo_line: int = 13  # page de départ KatawaJojo (13*8=104px, bas de l'écran 128px)
    luna_enabled: bool = False
    luna_line: int = 13  # page de départ Luna (13*8=104px, bas de l'écran 128px)
    ocean_dream_enabled: bool = False
    ocean_dream_line: int = 0  # plein écran
    bongo_enabled: bool = False
    bongo_line: int = 0  # page de départ Bongo Cat (0-15)
    crab_enabled: bool = False
    crab_line: int = 0  # page de départ Crab (0-15)
    # Widgets ZMK natifs (Phase 2 OLED custom ZMK) — ignorés en backend QMK.
    # Ils sont instanciés via les helpers `zmk_widget_*_init` de ZMK.
    zmk_battery: ZmkBatteryWidget = field(default_factory=ZmkBatteryWidget)
    zmk_output: OledOverlayItem = field(default_factory=OledOverlayItem)
    zmk_layer: OledOverlayItem = field(default_factory=OledOverlayItem)
    zmk_peripheral: OledOverlayItem = field(default_factory=OledOverlayItem)

    def to_dict(self) -> dict[str, Any]:
        return {
            "images": [img.to_dict() for img in self.images],
            "layer": self.layer.to_dict(),
            "caps_lock": self.caps_lock.to_dict(),
            "wpm": self.wpm.to_dict(),
            "rgb_mode": self.rgb_mode.to_dict(),
            "kfm": self.kfm.to_dict(),
            "katawajojo_enabled": self.katawajojo_enabled,
            "katawajojo_line": self.katawajojo_line,
            "luna_enabled": self.luna_enabled,
            "luna_line": self.luna_line,
            "ocean_dream_enabled": self.ocean_dream_enabled,
            "ocean_dream_line": self.ocean_dream_line,
            "bongo_enabled": self.bongo_enabled,
            "bongo_line": self.bongo_line,
            "crab_enabled": self.crab_enabled,
            "crab_line": self.crab_line,
            "zmk_battery": self.zmk_battery.to_dict(),
            "zmk_output": self.zmk_output.to_dict(),
            "zmk_layer": self.zmk_layer.to_dict(),
            "zmk_peripheral": self.zmk_peripheral.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledSideConfig":
        # New format: "images" key (list of OledImageItem dicts)
        if "images" in data and isinstance(data["images"], list):
            images = [OledImageItem.from_dict(d) for d in data["images"] if isinstance(d, dict)]
        # Migration: old format had image_path at top level
        elif data.get("image_path"):
            images = [OledImageItem.from_dict({
                "image_path": data["image_path"],
                "col": int(data.get("image_col", 0)),
                "line": int(data.get("image_line", 0)),
                "inverted": bool(data.get("image_inverted", False)),
            })]
        else:
            images = []
        # Migration: old "luna_enabled" was actually katawajojo
        if "katawajojo_enabled" in data:
            katawajojo_enabled = bool(data.get("katawajojo_enabled", False))
            katawajojo_line = int(data.get("katawajojo_line", 13))
            luna_enabled = bool(data.get("luna_enabled", False))
            luna_line = int(data.get("luna_line", 13))
        else:
            katawajojo_enabled = bool(data.get("luna_enabled", False))
            katawajojo_line = int(data.get("luna_line", 13))
            luna_enabled = False
            luna_line = 13
        return cls(
            images=images,
            layer=OledOverlayItem.from_dict(data.get("layer") or {}),
            caps_lock=OledOverlayItem.from_dict(data.get("caps_lock") or {}),
            wpm=OledOverlayItem.from_dict(data.get("wpm") or {}),
            rgb_mode=OledOverlayItem.from_dict(data.get("rgb_mode") or {}),
            kfm=OledOverlayItem.from_dict(data.get("kfm") or {}),
            katawajojo_enabled=katawajojo_enabled,
            katawajojo_line=katawajojo_line,
            luna_enabled=luna_enabled,
            luna_line=luna_line,
            ocean_dream_enabled=bool(data.get("ocean_dream_enabled", False)),
            ocean_dream_line=int(data.get("ocean_dream_line", 0)),
            bongo_enabled=bool(data.get("bongo_enabled", False)),
            bongo_line=int(data.get("bongo_line", 0)),
            crab_enabled=bool(data.get("crab_enabled", False)),
            crab_line=int(data.get("crab_line", 0)),
            zmk_battery=ZmkBatteryWidget.from_dict(data.get("zmk_battery") or {}),
            zmk_output=OledOverlayItem.from_dict(data.get("zmk_output") or {}),
            zmk_layer=OledOverlayItem.from_dict(data.get("zmk_layer") or {}),
            zmk_peripheral=OledOverlayItem.from_dict(data.get("zmk_peripheral") or {}),
        )


@dataclass
class OledConfig:
    """Configuration OLED split : côté gauche + côté droit indépendants.

    Migration : les anciens champs (image_path, overlays, luna_x, luna_y)
    sont ignorés silencieusement lors du chargement.
    """

    left: OledSideConfig = field(default_factory=OledSideConfig)
    right: OledSideConfig = field(default_factory=OledSideConfig)
    anti_burnin: bool = False
    sleep_enabled: bool = False
    sleep_timeout_s: int = 240
    use_builtin_screen: bool = False
    # Si True (ZMK uniquement) : force STATUS_SCREEN_BUILT_IN, ignore images+widgets.
    # Affiche le screen natif ZMK (layer + battery + output). L'éditeur canvas est
    # désactivé dans l'UI tant que cette option est cochée.
    show_battery_percentage: bool = False
    # Si True (ZMK uniquement) : affiche le pourcentage en texte à côté de l'icône
    # batterie. Active CONFIG_ZMK_WIDGET_BATTERY_STATUS_SHOW_PERCENTAGE=y.

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "anti_burnin": self.anti_burnin,
            "sleep_enabled": self.sleep_enabled,
            "sleep_timeout_s": self.sleep_timeout_s,
            "use_builtin_screen": self.use_builtin_screen,
            "show_battery_percentage": self.show_battery_percentage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OledConfig":
        # Migration : si l'ancien format (clé "image_path" au niveau racine) est détecté,
        # ignorer silencieusement les anciens champs.
        left_data = data.get("left") or {}
        right_data = data.get("right") or {}
        return cls(
            left=OledSideConfig.from_dict(left_data),
            right=OledSideConfig.from_dict(right_data),
            anti_burnin=bool(data.get("anti_burnin", False)),
            sleep_enabled=bool(data.get("sleep_enabled", False)),
            sleep_timeout_s=int(data.get("sleep_timeout_s", 240)),
            use_builtin_screen=bool(data.get("use_builtin_screen", False)),
            show_battery_percentage=bool(data.get("show_battery_percentage", False)),
        )


@dataclass
class KeyOffset:
    """Offset relatif d'une touche par rapport à la touche d'origine (row, col)."""

    dr: int = 0   # delta row (négatif = vers le haut)
    dc: int = 0   # delta col (négatif = vers la gauche)

    def to_dict(self) -> dict[str, int]:
        return {"dr": self.dr, "dc": self.dc}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeyOffset":
        return cls(dr=data.get("dr", 0), dc=data.get("dc", 0))


@dataclass
class EffectStep:
    """Un instant sur la timeline d'une piste d'effet custom.

    time_ms  : temps en ms depuis le déclenchement (T0 = appui ou début boucle).
    color    : couleur hex #RRGGBB de la LED à cet instant (couleur de départ).
    hold_ms  : durée de maintien de la couleur avant le fondu (0 = pas de maintien).
    fade_ms  : durée du fondu (0 = pas de fondu, la LED reste à ``color``).
    color_to : couleur d'arrivée du fondu ("" = pas de transition).
    """

    time_ms: int = 0
    color: str = "#FFFFFF"
    hold_ms: int = 0
    fade_ms: int = 0
    color_to: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"time_ms": self.time_ms, "color": self.color}
        if self.hold_ms:
            d["hold_ms"] = self.hold_ms
        if self.fade_ms:
            d["fade_ms"] = self.fade_ms
        if self.color_to:
            d["color_to"] = self.color_to
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EffectStep":
        return cls(
            time_ms=data.get("time_ms", 0),
            color=data.get("color", "#FFFFFF"),
            hold_ms=data.get("hold_ms", 0),
            fade_ms=data.get("fade_ms", 0),
            color_to=data.get("color_to", ""),
        )


@dataclass
class EffectTrack:
    """Piste d'animation dans un effet custom.

    target_mode :
      - "default"  → touche qui a déclenché l'effet (réactif uniquement)
      - "relative" → offsets par rapport à la touche d'origine
      - "fixed"    → touches absolues identifiées par key_id
    keys_offset  : liste d'offsets (utilisé si target_mode == "relative")
    keys_fixed   : liste de key_id (utilisé si target_mode == "fixed")
    steps        : étapes temporelles de cette piste
    """

    name: str = "Piste 1"
    enabled: bool = True
    target_mode: str = "default"  # "default" | "relative" | "fixed"
    trigger_keys: list[str] = field(default_factory=list)  # key_ids déclencheurs (vide = toutes)
    keys_offset: list[KeyOffset] = field(default_factory=list)
    keys_fixed: list[str] = field(default_factory=list)  # ex: ["L_r2_c3", "R_r0_c5"]
    steps: list[EffectStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "target_mode": self.target_mode,
            "steps": [s.to_dict() for s in self.steps],
        }
        if not self.enabled:
            d["enabled"] = False
        if self.trigger_keys:
            d["trigger_keys"] = list(self.trigger_keys)
        if self.target_mode == "relative" and self.keys_offset:
            d["keys_offset"] = [k.to_dict() for k in self.keys_offset]
        if self.target_mode == "fixed" and self.keys_fixed:
            d["keys_fixed"] = list(self.keys_fixed)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EffectTrack":
        return cls(
            name=data.get("name", "Piste 1"),
            enabled=bool(data.get("enabled", True)),
            target_mode=data.get("target_mode", "default"),
            trigger_keys=list(data.get("trigger_keys") or []),
            keys_offset=[KeyOffset.from_dict(k) for k in (data.get("keys_offset") or [])],
            keys_fixed=list(data.get("keys_fixed") or []),
            steps=[EffectStep.from_dict(s) for s in (data.get("steps") or [])],
        )


@dataclass
class CustomEffect:
    """Effet RGB custom créé par l'utilisateur via l'éditeur timeline.

    effect_type :
      - "reactive" → déclenché par l'appui d'une touche
      - "ambient"  → boucle en continu sans appui
    tracks : pistes d'animation indépendantes (chacune avec sa timeline)
    """

    name: str = "Mon effet"
    effect_type: str = "reactive"  # "reactive" | "ambient"
    tracks: list[EffectTrack] = field(default_factory=list)
    custom_code: str | None = None  # code C édité manuellement (bypass Jinja2)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "effect_type": self.effect_type,
            "tracks": [t.to_dict() for t in self.tracks],
        }
        if self.custom_code is not None:
            d["custom_code"] = self.custom_code
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomEffect":
        return cls(
            name=data.get("name", "Mon effet"),
            effect_type=data.get("effect_type", "reactive"),
            tracks=[EffectTrack.from_dict(t) for t in (data.get("tracks") or [])],
            custom_code=data.get("custom_code"),
        )


@dataclass
class RgbEffect:
    """Définition d'un effet RGB.

    Couleurs stockées en hex #RRGGBB.
    """

    type: str = "static"
    color_primary: str = "#FFFFFF"
    color_secondary: str = "#888888"
    fade_ms: int = 500
    speed: int = 128          # QMK RGB_MATRIX_DEFAULT_SPD (0-255)
    brightness: int = 128     # QMK RGB_MATRIX_DEFAULT_VAL (0-255)
    trigger_key: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "color_primary": self.color_primary,
            "color_secondary": self.color_secondary,
            "fade_ms": self.fade_ms,
            "speed": self.speed,
            "brightness": self.brightness,
            "trigger_key": self.trigger_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RgbEffect":
        def _int(key: str, default: int) -> int:
            try:
                return int(data.get(key, default))
            except (ValueError, TypeError):
                return default
        return cls(
            type=str(data.get("type", "static")),
            color_primary=str(data.get("color_primary", "#FFFFFF")),
            color_secondary=str(data.get("color_secondary", "#888888")),
            fade_ms=_int("fade_ms", 500),
            speed=max(0, min(255, _int("speed", 128))),
            brightness=max(0, min(255, _int("brightness", 128))),
            trigger_key=data.get("trigger_key"),
        )


@dataclass
class RgbConfig:
    """Configuration RGB globale (effets prédéfinis + couleurs par touche)."""

    effects: list[RgbEffect] = field(default_factory=list)
    per_key: dict[str, str] = field(default_factory=dict)
    enabled_effects: list[str] = field(default_factory=list)  # vide = tous activés
    custom_effects: list[CustomEffect] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "effects": [e.to_dict() for e in self.effects],
            "per_key": dict(self.per_key),
        }
        if self.enabled_effects:
            d["enabled_effects"] = list(self.enabled_effects)
        if self.custom_effects:
            d["custom_effects"] = [ce.to_dict() for ce in self.custom_effects]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RgbConfig":
        return cls(
            effects=[RgbEffect.from_dict(e) for e in (data.get("effects") or []) if isinstance(e, dict)],
            per_key=dict(data.get("per_key") or {}),
            enabled_effects=list(data.get("enabled_effects") or []),
            custom_effects=[CustomEffect.from_dict(ce) for ce in (data.get("custom_effects") or []) if isinstance(ce, dict)],
        )


@dataclass
class AdvancedOptionsConfig:
    """Options avancées de firmware exposées via l'onglet "Options avancées".

    Une seule classe pour QMK + ZMK : chaque option a un commentaire indiquant
    sur quel firmware elle s'applique. Les options "non concernées" sont
    visibles dans l'UI mais grisées avec un tooltip explicatif.

    Mapping vers les Kconfig / #define se fait dans les template generators
    (ZMK : `shield.conf.j2`, QMK : `config.h.j2`).
    Voir `~/.claude/projects/.../memory/firmware_options_catalog.md` pour la
    référence complète des options et leur effet détaillé.
    """

    # ── Identification (commun) ──────────────────────────────────────────────
    keyboard_name: str = ""
    """Nom BLE/USB affiché par l'OS. Vide = laisser le défaut firmware."""

    # ── Comportement clavier (commun) ────────────────────────────────────────
    nkro_enabled: bool = False
    """N-Key Rollover. QMK : `NKRO_ENABLE` + `FORCE_NKRO`. ZMK : `ZMK_HID_REPORT_TYPE_NKRO`."""
    hid_indicators_enabled: bool = True
    """Reçoit CapsLock/NumLock/ScrollLock de l'OS. ZMK : `ZMK_HID_INDICATORS=y` (défaut ON
    car utile pour afficher CapsLock sur OLED). QMK : disponible nativement."""
    usb_boot_protocol: bool = False
    """Compat BIOS (HID Boot Protocol supplémentaire). ZMK : `ZMK_USB_BOOT=y`. QMK : -."""
    auto_shift_enabled: bool = False  # QMK uniquement
    """Maintenir une touche → version shiftée. QMK : `AUTO_SHIFT_ENABLE`."""
    auto_shift_timeout_ms: int = 175  # QMK uniquement
    """Délai auto-shift. QMK : `AUTO_SHIFT_TIMEOUT`."""

    # ── Bluetooth (ZMK uniquement) ───────────────────────────────────────────
    ble_passkey_entry: bool = False
    """Code à 6 chiffres lors du pairing. ZMK : `ZMK_BLE_PASSKEY_ENTRY=y`."""

    # ── Énergie ──────────────────────────────────────────────────────────────
    deep_sleep_timeout_min: int = 4
    """Délai avant deep sleep (ZMK). Mappé à `ZMK_IDLE_SLEEP_TIMEOUT` en ms."""
    battery_report_interval_s: int = 60
    """Fréquence de rapport batterie. ZMK : `ZMK_BATTERY_REPORT_INTERVAL` (s)."""
    soft_off_enabled: bool = False
    """Touche `&soft_off` propre. ZMK : `ZMK_PM_SOFT_OFF=y` + `ZMK_BEHAVIOR_SOFT_OFF=y`."""

    # ── Behaviors ergo ───────────────────────────────────────────────────────
    tap_dance_enabled: bool = False
    """Multi-tap behaviors. ZMK : `ZMK_BEHAVIOR_TAP_DANCE=y`. QMK : `TAP_DANCE_ENABLE`."""
    sticky_key_enabled: bool = False
    """One-shot modifiers. ZMK : `ZMK_BEHAVIOR_STICKY_KEY=y`. QMK : `STICKY_KEYS`."""
    tapping_term_ms: int = 200  # QMK uniquement (équivalent par-binding en ZMK)
    """Durée tap avant hold. QMK : `TAPPING_TERM`."""
    combo_term_ms: int = 50  # QMK uniquement
    """Durée max entre touches d'un combo. QMK : `COMBO_TERM`."""
    permissive_hold: bool = False  # QMK uniquement
    """Hold même si autre touche pressée pendant le tap. QMK : `PERMISSIVE_HOLD`."""

    # ── RGB avancé ───────────────────────────────────────────────────────────
    rgb_hue_start: int = 0
    """Couleur de démarrage en HUE 0-359 (0=rouge, 120=vert, 240=bleu).
    ZMK : `ZMK_RGB_UNDERGLOW_HUE_START`. QMK : startup color via custom code."""
    rgb_on_start: bool = True
    """RGB allumé au boot (par défaut True). ZMK : `ZMK_RGB_UNDERGLOW_ON_START`."""
    rgb_auto_off_idle: bool = False
    """Éteint RGB en idle (économie batterie). ZMK : `ZMK_RGB_UNDERGLOW_AUTO_OFF_IDLE`."""
    rgb_auto_off_usb: bool = False
    """Éteint RGB quand USB débranché. ZMK : `ZMK_RGB_UNDERGLOW_AUTO_OFF_USB`."""

    # ── Pointing (ZMK uniquement) ────────────────────────────────────────────
    pointing_enabled: bool = False
    """Support trackball/touchpad/trackpoint. ZMK : `ZMK_POINTING=y`."""
    pointing_smooth_scroll: bool = False
    """Scroll high-res. ZMK : `ZMK_POINTING_SMOOTH_SCROLLING=y`."""

    # ── Mouse keys (QMK uniquement) ──────────────────────────────────────────
    mousekey_enabled: bool = False
    """Active la fonctionnalité Mouse Keys ; sinon les réglages ci-dessous sont
    ignorés. QMK : `MOUSEKEY_ENABLE`."""
    mousekey_delay_ms: int = 10
    """Délai initial mouvement. QMK : `MOUSEKEY_DELAY`."""
    mousekey_interval_ms: int = 20
    """Intervalle entre mouvements. QMK : `MOUSEKEY_INTERVAL`."""
    mousekey_max_speed: int = 10
    """Vitesse max curseur. QMK : `MOUSEKEY_MAX_SPEED`."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyboard_name": self.keyboard_name,
            "nkro_enabled": self.nkro_enabled,
            "hid_indicators_enabled": self.hid_indicators_enabled,
            "usb_boot_protocol": self.usb_boot_protocol,
            "auto_shift_enabled": self.auto_shift_enabled,
            "auto_shift_timeout_ms": self.auto_shift_timeout_ms,
            "ble_passkey_entry": self.ble_passkey_entry,
            "deep_sleep_timeout_min": self.deep_sleep_timeout_min,
            "battery_report_interval_s": self.battery_report_interval_s,
            "soft_off_enabled": self.soft_off_enabled,
            "tap_dance_enabled": self.tap_dance_enabled,
            "sticky_key_enabled": self.sticky_key_enabled,
            "tapping_term_ms": self.tapping_term_ms,
            "combo_term_ms": self.combo_term_ms,
            "permissive_hold": self.permissive_hold,
            "rgb_hue_start": self.rgb_hue_start,
            "rgb_on_start": self.rgb_on_start,
            "rgb_auto_off_idle": self.rgb_auto_off_idle,
            "rgb_auto_off_usb": self.rgb_auto_off_usb,
            "pointing_enabled": self.pointing_enabled,
            "pointing_smooth_scroll": self.pointing_smooth_scroll,
            "mousekey_enabled": self.mousekey_enabled,
            "mousekey_delay_ms": self.mousekey_delay_ms,
            "mousekey_interval_ms": self.mousekey_interval_ms,
            "mousekey_max_speed": self.mousekey_max_speed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdvancedOptionsConfig":
        return cls(
            keyboard_name=str(data.get("keyboard_name", "")),
            nkro_enabled=bool(data.get("nkro_enabled", False)),
            hid_indicators_enabled=bool(data.get("hid_indicators_enabled", True)),
            usb_boot_protocol=bool(data.get("usb_boot_protocol", False)),
            auto_shift_enabled=bool(data.get("auto_shift_enabled", False)),
            auto_shift_timeout_ms=max(50, int(data.get("auto_shift_timeout_ms", 175))),
            ble_passkey_entry=bool(data.get("ble_passkey_entry", False)),
            deep_sleep_timeout_min=max(1, int(data.get("deep_sleep_timeout_min", 4))),
            battery_report_interval_s=max(10, int(data.get("battery_report_interval_s", 60))),
            soft_off_enabled=bool(data.get("soft_off_enabled", False)),
            tap_dance_enabled=bool(data.get("tap_dance_enabled", False)),
            sticky_key_enabled=bool(data.get("sticky_key_enabled", False)),
            tapping_term_ms=max(50, int(data.get("tapping_term_ms", 200))),
            combo_term_ms=max(10, int(data.get("combo_term_ms", 50))),
            permissive_hold=bool(data.get("permissive_hold", False)),
            rgb_hue_start=max(0, min(359, int(data.get("rgb_hue_start", 0)))),
            rgb_on_start=bool(data.get("rgb_on_start", True)),
            rgb_auto_off_idle=bool(data.get("rgb_auto_off_idle", False)),
            rgb_auto_off_usb=bool(data.get("rgb_auto_off_usb", False)),
            pointing_enabled=bool(data.get("pointing_enabled", False)),
            pointing_smooth_scroll=bool(data.get("pointing_smooth_scroll", False)),
            mousekey_enabled=bool(data.get("mousekey_enabled", False)),
            mousekey_delay_ms=max(1, int(data.get("mousekey_delay_ms", 10))),
            mousekey_interval_ms=max(1, int(data.get("mousekey_interval_ms", 20))),
            mousekey_max_speed=max(1, int(data.get("mousekey_max_speed", 10))),
        )


@dataclass
class BuildConfig:
    """Versions de la toolchain verrouillées pour la reproductibilité."""

    vial_qmk_version: str = ""
    toolchain_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "vial_qmk_version": self.vial_qmk_version,
            "toolchain_version": self.toolchain_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildConfig":
        return cls(
            vial_qmk_version=data.get("vial_qmk_version", ""),
            toolchain_version=data.get("toolchain_version", ""),
        )


@dataclass
class ProjectModel:
    """État central sérialisable de keyboard_firmware_maker.

    Passé par injection de dépendance à chaque widget via le constructeur.
    Ne jamais instancier en singleton global.

    Format JSON de sauvegarde (clés snake_case) :
    {
        "version": "1.0",
        "keyboard": {"model": "sofle-v2", "mcu": "rp2040"},
        "oled": {
            "left":  {"images": [{"image_path": "", "col": 0, "line": 0, ...}], "layer": {...}, ...},
            "right": {"images": [], "layer": {...}, ...}
        },
        "rgb": {"effects": [...], "per_key": {"KEY_A": "#FF0000"}},
        "build": {"vial_qmk_version": "0.7.1", "toolchain_version": "13.3.rel1"}
    }
    """

    version: str = "1.0"
    keyboard: KeyboardConfig = field(default_factory=KeyboardConfig)
    oled: OledConfig = field(default_factory=OledConfig)
    rgb: RgbConfig = field(default_factory=RgbConfig)
    advanced: AdvancedOptionsConfig = field(default_factory=AdvancedOptionsConfig)
    build: BuildConfig = field(default_factory=BuildConfig)

    def to_dict(self) -> dict[str, Any]:
        """Sérialise l'état complet en dict JSON-compatible.

        Note: OledSideConfig.frames est exclu (données binaires runtime).
        """
        return {
            "version": self.version,
            "keyboard": self.keyboard.to_dict(),
            "oled": self.oled.to_dict(),
            "rgb": self.rgb.to_dict(),
            "advanced": self.advanced.to_dict(),
            "build": self.build.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectModel":
        """Reconstruit un ProjectModel depuis un dict JSON.

        Gère les dicts partiels (champs manquants → valeurs par défaut).
        """
        return cls(
            version=data.get("version", "1.0"),
            keyboard=KeyboardConfig.from_dict(data.get("keyboard") or {}),
            oled=OledConfig.from_dict(data.get("oled") or {}),
            rgb=RgbConfig.from_dict(data.get("rgb") or {}),
            advanced=AdvancedOptionsConfig.from_dict(data.get("advanced") or {}),
            build=BuildConfig.from_dict(data.get("build") or {}),
        )
