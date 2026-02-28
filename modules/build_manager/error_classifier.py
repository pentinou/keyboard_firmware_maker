"""error_classifier.py — Classification des erreurs de compilation QMK (FR21, FR22).

Analyse les lignes de log make/gcc et retourne un message lisible + un diagnostic
actionnable. Aucun import Qt — pur Python.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (pattern, pattern_name, message_lisible, diagnostic_actionnable)
_ERROR_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    (
        re.compile(
            r"arm-none-eabi-gcc.*(not found|no such file)|command not found.*gcc",
            re.IGNORECASE,
        ),
        "toolchain_missing",
        "La toolchain ARM est introuvable.",
        "Vérifiez que arm-none-eabi-gcc est installé sur votre système.\n"
        "• Ubuntu/Debian : sudo apt install gcc-arm-none-eabi\n"
        "• Windows       : https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads",
    ),
    (
        re.compile(r"error:.*unknown type name|error:.*undeclared identifier", re.IGNORECASE),
        "syntax_error",
        "Erreur de syntaxe dans le code QMK généré.",
        "Un paramètre de configuration invalide a été détecté.\n"
        "Vérifiez les options RGB ou OLED dans votre projet.",
    ),
    (
        re.compile(r"undefined reference to", re.IGNORECASE),
        "linker_error",
        "Erreur de liaison (linker) : fonction non définie.",
        "Une fonction QMK requise est manquante.\n"
        "Vérifiez que les bons modules sont activés dans rules.mk\n"
        "(ex : OLED_ENABLE, RGB_MATRIX_ENABLE).",
    ),
    (
        re.compile(
            r"region .* overflowed|firmware too large|will not fit in program space",
            re.IGNORECASE,
        ),
        "flash_overflow",
        "Le firmware est trop volumineux pour le microcontrôleur.",
        "Désactivez certaines fonctionnalités (OLED, RGB Matrix, WPM)\n"
        "pour réduire la taille du firmware.",
    ),
    (
        re.compile(r"No rule to make target|no targets specified", re.IGNORECASE),
        "make_target_missing",
        "Cible de compilation introuvable dans le répertoire Vial-QMK.",
        "Le cache Vial-QMK est peut-être corrompu.\n"
        "Supprimez ~/.keyboard_firmware_maker/vial-qmk et relancez l'application.",
    ),
    (
        re.compile(r"TemplateNotFound|jinja2.*error|TemplateSyntaxError", re.IGNORECASE),
        "template_error",
        "Erreur dans les templates de génération du code.",
        "Les templates Jinja2 sont manquants ou corrompus.\n"
        "Réinstallez l'application.",
    ),
    (
        re.compile(r"cannot open output file|permission denied", re.IGNORECASE),
        "permission_error",
        "Impossible d'écrire les fichiers de compilation.",
        "Vérifiez les droits d'accès au répertoire de cache\n"
        "(~/.keyboard_firmware_maker/).",
    ),
    (
        re.compile(
            r"VIAL_ENABLE in rules\.mk is no longer a valid option",
            re.IGNORECASE,
        ),
        "vial_enable_deprecated",
        "VIAL_ENABLE dans rules.mk n'est plus valide (Vial-QMK moderne).",
        "Ce problème a été corrigé dans les templates.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(
            r"DESCRIPTION in config\.h is no longer a valid option",
            re.IGNORECASE,
        ),
        "description_deprecated",
        "DESCRIPTION dans config.h est obsolète (QMK moderne).",
        "Ce problème a été corrigé dans les templates.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(
            r"No LAYOUTs defined|Need at least one layout defined in info\.json",
            re.IGNORECASE,
        ),
        "no_layout_defined",
        "Aucun layout défini dans info.json.",
        "Ce problème a été corrigé : info.json est maintenant généré avec LAYOUT_sofle.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(
            r"Invalid RGB_MATRIX_DRIVER|RGB_MATRIX_DRIVER.*is not a valid matrix type",
            re.IGNORECASE,
        ),
        "rgb_matrix_driver_invalid",
        "RGB_MATRIX_DRIVER invalide ou manquant dans rules.mk.",
        "Ce problème a été corrigé : RGB_MATRIX_DRIVER = WS2812 est maintenant défini.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(r"RGB_DI_PIN.*no longer a valid option", re.IGNORECASE),
        "rgb_di_pin_deprecated",
        "RGB_DI_PIN dans config.h est obsolète (remplacé par WS2812_DI_PIN).",
        "Ce problème a été corrigé dans les templates.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(
            r"rgb_matrix\.driver.*is not one of|Invalid API data.*rgb_matrix",
            re.IGNORECASE,
        ),
        "rgb_matrix_driver_case",
        "Valeur RGB_MATRIX_DRIVER invalide (casse incorrecte ou driver inconnu).",
        "Ce problème a été corrigé : le driver 'ws2812' est maintenant en minuscules.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(r"Platform not defined", re.IGNORECASE),
        "platform_not_defined",
        "Plateforme microcontrôleur non reconnue par QMK.",
        "Vérifiez que le MCU (ex: RP2040) est correctement défini dans rules.mk.\n"
        "Si l'erreur persiste après regénération, vérifiez les erreurs API ci-dessus.",
    ),
    (
        re.compile(r"Please use.*vendor.*WS2812 driver for RP2040", re.IGNORECASE),
        "ws2812_bitbang_rp2040",
        "Le driver WS2812 bitbang n'est pas supporté sur RP2040.",
        "Ce problème a été corrigé : WS2812_DRIVER = vendor est maintenant défini.\n"
        "Regénérez le firmware depuis l'application.",
    ),
    (
        re.compile(r"palWaitLineTimeout|palEnablePadEvent.*implicit", re.IGNORECASE),
        "serial_bitbang_rp2040",
        "Le driver série bitbang n'est pas supporté sur RP2040.",
        "Ce problème a été corrigé : SERIAL_DRIVER = vendor est maintenant défini.\n"
        "Regénérez le firmware depuis l'application.",
    ),
]

_GENERIC_MESSAGE = "La compilation a échoué."
_GENERIC_DIAGNOSIS = (
    "Consultez les logs ci-dessus pour le détail de l'erreur.\n"
    "Si le problème persiste, vérifiez la compatibilité de votre configuration."
)


@dataclass
class ErrorDiagnosis:
    """Résultat de la classification d'une erreur de compilation."""

    message: str                 # message lisible court (FR21)
    diagnosis: str               # diagnostic actionnable (FR22)
    pattern_matched: str | None  # nom du pattern, None si générique


def classify_build_error(log_lines: list[str]) -> ErrorDiagnosis:
    """Analyse les lignes de log et retourne un diagnostic lisible.

    Parcourt les patterns dans l'ordre et retourne le premier match.
    Si aucun pattern ne correspond, retourne un message générique.

    Args:
        log_lines: liste des lignes de log émises pendant le build.

    Returns:
        ErrorDiagnosis avec message humanisé et diagnostic.
    """
    full_log = "\n".join(log_lines)
    for pattern, name, message, diagnosis in _ERROR_PATTERNS:
        if pattern.search(full_log):
            return ErrorDiagnosis(
                message=message,
                diagnosis=diagnosis,
                pattern_matched=name,
            )
    return ErrorDiagnosis(
        message=_GENERIC_MESSAGE,
        diagnosis=_GENERIC_DIAGNOSIS,
        pattern_matched=None,
    )
