"""Strings de l'interface utilisateur en FR / EN / IT."""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        # Application
        "app.title": "keyboard_firmware_maker",
        # Menus
        "menu.file": "Fichier",
        "menu.file.save": "Sauvegarder le projet\u2026",
        "menu.file.open": "Ouvrir un projet\u2026",
        "menu.file.quit": "Quitter",
        "menu.help": "Aide",
        "menu.help.about": "\u00c0 propos\u2026",
        "menu.config": "Configuration",
        "menu.config.language": "Langue",
        # Onglets
        "tab.hardware": "Mat\u00e9riel",
        "tab.oled": "OLED",
        "tab.rgb": "RGB",
        "tab.build": "Build",
        # RGB widget
        "rgb.instructions": "Couleurs par touche \u2014 cliquez une touche pour assigner une couleur",
        "rgb.effects_group": "Effets RGB",
        "rgb.static.color": "Couleur uniforme :",
        "rgb.static.tooltip": "Cliquer pour choisir la couleur",
        "rgb.native.info": "Effet natif QMK \u2014 ajustable via RGB_MOD / RGB_HUI / RGB_VAI sur le clavier.",
        "rgb.ripple.primary": "Couleur touche press\u00e9e :",
        "rgb.ripple.secondary": "Couleur touches voisines :",
        "rgb.ripple.fade": "Vitesse de fondu (ms) :",
        "rgb.ripple.trigger_btn": "Choisir touche d\u00e9clencheur",
        "rgb.ripple.trigger_none": "Non d\u00e9fini",
        "rgb.ripple.trigger_click": "Cliquez une touche\u2026",
        "rgb.dialog.primary_color": "Couleur principale",
        "rgb.dialog.secondary_color": "Couleur secondaire",
        "rgb.key_color_fmt": "Couleur pour {key_id}",
        # Dialogues
        "dlg.error": "Erreur",
        "dlg.save_error": "Impossible de sauvegarder : {e}",
        "dlg.load_error": "Impossible de charger le projet : {e}",
        "dlg.vial_unavailable": "Vial-QMK non disponible",
        "dlg.vial_unavailable_msg": (
            "La configuration de Vial-QMK a \u00e9chou\u00e9 ou a \u00e9t\u00e9 annul\u00e9e.\n"
            "L'onglet Build ne fonctionnera pas correctement.\n"
            "Relancez l'application pour r\u00e9essayer."
        ),
        "dlg.lang_change_title": "Langue modifi\u00e9e",
        "dlg.lang_change_msg": "La langue sera appliqu\u00e9e au prochain d\u00e9marrage.",
        "dlg.save_title": "Sauvegarder le projet",
        "dlg.open_title": "Ouvrir un projet",
        "dlg.file_filter": "Projet KFM (*.kfm.json)",
    },
    "en": {
        # Application
        "app.title": "keyboard_firmware_maker",
        # Menus
        "menu.file": "File",
        "menu.file.save": "Save project\u2026",
        "menu.file.open": "Open project\u2026",
        "menu.file.quit": "Quit",
        "menu.help": "Help",
        "menu.help.about": "About\u2026",
        "menu.config": "Configuration",
        "menu.config.language": "Language",
        # Tabs
        "tab.hardware": "Hardware",
        "tab.oled": "OLED",
        "tab.rgb": "RGB",
        "tab.build": "Build",
        # RGB widget
        "rgb.instructions": "Per-key colors \u2014 click a key to assign a color",
        "rgb.effects_group": "RGB Effects",
        "rgb.static.color": "Uniform color:",
        "rgb.static.tooltip": "Click to choose color",
        "rgb.native.info": "Native QMK effect \u2014 adjustable via RGB_MOD / RGB_HUI / RGB_VAI on the keyboard.",
        "rgb.ripple.primary": "Pressed key color:",
        "rgb.ripple.secondary": "Neighbor keys color:",
        "rgb.ripple.fade": "Fade speed (ms):",
        "rgb.ripple.trigger_btn": "Choose trigger key",
        "rgb.ripple.trigger_none": "Not defined",
        "rgb.ripple.trigger_click": "Click a key\u2026",
        "rgb.dialog.primary_color": "Primary color",
        "rgb.dialog.secondary_color": "Secondary color",
        "rgb.key_color_fmt": "Color for {key_id}",
        # Dialogs
        "dlg.error": "Error",
        "dlg.save_error": "Cannot save: {e}",
        "dlg.load_error": "Cannot load project: {e}",
        "dlg.vial_unavailable": "Vial-QMK unavailable",
        "dlg.vial_unavailable_msg": (
            "Vial-QMK setup failed or was cancelled.\n"
            "The Build tab will not work correctly.\n"
            "Restart the application to try again."
        ),
        "dlg.lang_change_title": "Language changed",
        "dlg.lang_change_msg": "The language will be applied on next startup.",
        "dlg.save_title": "Save project",
        "dlg.open_title": "Open project",
        "dlg.file_filter": "KFM project (*.kfm.json)",
    },
    "it": {
        # Applicazione
        "app.title": "keyboard_firmware_maker",
        # Menu
        "menu.file": "File",
        "menu.file.save": "Salva progetto\u2026",
        "menu.file.open": "Apri progetto\u2026",
        "menu.file.quit": "Esci",
        "menu.help": "Aiuto",
        "menu.help.about": "Informazioni\u2026",
        "menu.config": "Configurazione",
        "menu.config.language": "Lingua",
        # Schede
        "tab.hardware": "Hardware",
        "tab.oled": "OLED",
        "tab.rgb": "RGB",
        "tab.build": "Build",
        # Widget RGB
        "rgb.instructions": "Colori per tasto \u2014 clicca un tasto per assegnare un colore",
        "rgb.effects_group": "Effetti RGB",
        "rgb.static.color": "Colore uniforme:",
        "rgb.static.tooltip": "Clicca per scegliere il colore",
        "rgb.native.info": "Effetto nativo QMK \u2014 regolabile tramite RGB_MOD / RGB_HUI / RGB_VAI sulla tastiera.",
        "rgb.ripple.primary": "Colore tasto premuto:",
        "rgb.ripple.secondary": "Colore tasti vicini:",
        "rgb.ripple.fade": "Velocit\u00e0 dissolvenza (ms):",
        "rgb.ripple.trigger_btn": "Scegli tasto trigger",
        "rgb.ripple.trigger_none": "Non definito",
        "rgb.ripple.trigger_click": "Clicca un tasto\u2026",
        "rgb.dialog.primary_color": "Colore principale",
        "rgb.dialog.secondary_color": "Colore secondario",
        "rgb.key_color_fmt": "Colore per {key_id}",
        # Dialoghi
        "dlg.error": "Errore",
        "dlg.save_error": "Impossibile salvare: {e}",
        "dlg.load_error": "Impossibile caricare il progetto: {e}",
        "dlg.vial_unavailable": "Vial-QMK non disponibile",
        "dlg.vial_unavailable_msg": (
            "La configurazione di Vial-QMK \u00e8 fallita o \u00e8 stata annullata.\n"
            "La scheda Build non funzioner\u00e0 correttamente.\n"
            "Riavvia l'applicazione per riprovare."
        ),
        "dlg.lang_change_title": "Lingua modificata",
        "dlg.lang_change_msg": "La lingua sar\u00e0 applicata al prossimo avvio.",
        "dlg.save_title": "Salva progetto",
        "dlg.open_title": "Apri progetto",
        "dlg.file_filter": "Progetto KFM (*.kfm.json)",
    },
}
