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
        # Boutons génériques
        "btn.close": "Fermer",
        "btn.previous": "Pr\u00e9c\u00e9dent",
        "btn.next": "Suivant",
        # Onglet Matériel
        "hardware.keyboard_model": "Mod\u00e8le de clavier :",
        "hardware.mcu": "Microcontr\u00f4leur :",
        "hardware.layout_variant": "Variante de layout :",
        "hardware.oled": "\u00c9crans OLED :",
        "hardware.rgb": "RGB (underglow / per-key) :",
        "hardware.oled.none": "Aucun",
        "hardware.oled.left_only": "Gauche seulement",
        "hardware.oled.right_only": "Droite seulement",
        "hardware.oled.both": "Gauche et droite",
        # Onglet OLED
        "oled.side.left": "Gauche",
        "oled.side.right": "Droite",
        "oled.import_btn": "Importer image\u2026",
        "oled.group.utils": "Utilitaires",
        "oled.group.eyecandy": "Eye Candy",
        "oled.overlay.layer": "Layer",
        "oled.overlay.caps_lock": "Caps Lock",
        "oled.overlay.wpm": "WPM",
        "oled.overlay.rgb_mode": "Animation RGB",
        "oled.overlay.kfm": "<KFM>\u2122",
        "oled.overlay.katawajojo": "KatawaJojo",
        "oled.overlay.luna": "Luna",
        "oled.overlay.ocean_dream": "Ocean Dream",
        "oled.overlay.bongo": "Bongo Cat",
        "oled.overlay.crab": "Crabe",
        "oled.btn.negative": "N\u00e9gatif",
        "oled.btn.rotate": "Rotation 90\u00b0",
        "oled.btn.reset": "R\u00e9initialiser \u00e9cran",
        "oled.anti_burnin": "Anti-marquage (inversion 1\u00a0s / minute)",
        "oled.sleep": "Mode veille (écrans + lumières)",
        "oled.sleep_timeout": "Délai d'inactivité (s) :",
        "oled.import_dialog_title": "Importer une image",
        "oled.image_filter": "Images (*.png *.bmp *.gif)",
        "oled.import_error_title": "Erreur d\u2019import",
        "oled.import_error_msg": "Impossible de charger l\u2019image : {msg}",
        # Onglet Build
        "build.btn.generate": "G\u00e9n\u00e9rer firmware",
        "build.btn.export": "Exporter le firmware",
        "build.btn.guide": "Guide de flash",
        "build.toolchain_found": "Toolchain : {gcc_path}  |  version {version}  |  source : {source}",
        "build.toolchain_not_found": "\u26a0 Toolchain introuvable\n{msg}",
        "build.toolchain_missing_title": "Toolchain introuvable",
        "build.vial_not_init_title": "Vial-QMK non initialis\u00e9",
        "build.vial_not_init_msg": (
            "Vial-QMK n\u2019est pas disponible dans le cache.\n"
            "Relancez l\u2019application pour le t\u00e9l\u00e9charger."
        ),
        "build.compiling": "Compilation en cours\u2026",
        "build.firmware_size": "Firmware : {size_kb} KB / {flash_kb} KB utilis\u00e9s",
        "build.oversized_title": "Firmware trop volumineux",
        "build.oversized_msg": (
            "Le firmware ({size_kb} KB) d\u00e9passe la capacit\u00e9 flash du MCU "
            "{mcu} ({flash_kb} KB).\n"
            "R\u00e9duisez les fonctionnalit\u00e9s activ\u00e9es avant de flasher."
        ),
        "build.success": "Compilation r\u00e9ussie.",
        "build.error": "\u00c9chec de la compilation.",
        "build.error_title": "Erreur de compilation",
        "build.file_not_found_title": "Fichier introuvable",
        "build.file_not_found_msg": (
            "Le fichier firmware n\u2019est plus disponible.\n"
            "Relancez une compilation avant d\u2019exporter."
        ),
        "build.export_dialog_title": "Exporter le firmware",
        "build.uf2_filter": "Firmware UF2 (*.uf2)",
        "build.export_error_title": "Erreur d\u2019export",
        "build.export_error_msg": "Impossible d\u2019exporter le firmware :\n{exc}",
        "build.export_success_title": "Export r\u00e9ussi",
        "build.export_success_msg": "Firmware export\u00e9 vers :\n{dest}",
        # Dialogue À propos
        "about.title": "\u00c0 propos \u2014 keyboard_firmware_maker {version}",
        "about.version": "Version : {version}",
        "about.description": (
            "Application desktop pour cr\u00e9er et personnaliser des firmwares\n"
            "QMK/Vial-QMK pour claviers m\u00e9caniques split."
        ),
        # Dialogue Guide de flash
        "flash_guide.title": "Guide de flash du firmware",
        "flash_guide.progress": "\u00c9tape {current} / {total}",
        "flash_guide.missing_image": "[image manquante : {name}]",
        "flash_guide.step1_title": "\u00c9tape 1 : Localiser le bouton BOOT",
        "flash_guide.step1_text": (
            "Sur le PCB de votre Sofle, rep\u00e9rez le bouton marqu\u00e9 BOOT\n"
            "(souvent pr\u00e8s du microcontr\u00f4leur RP2040)."
        ),
        "flash_guide.step2_title": "\u00c9tape 2 : Entrer en mode bootloader",
        "flash_guide.step2_text": (
            "1. Maintenez le bouton BOOT appuy\u00e9\n"
            "2. Branchez le c\u00e2ble USB \u00e0 votre clavier\n"
            "3. Rel\u00e2chez le bouton BOOT"
        ),
        "flash_guide.step3_title": "\u00c9tape 3 : Lecteur RPI-RP2 d\u00e9tect\u00e9",
        "flash_guide.step3_text": (
            "Un lecteur nomm\u00e9 \u2018RPI-RP2\u2019 appara\u00eet dans votre explorateur de fichiers.\n"
            "Si le lecteur n\u2019appara\u00eet pas, r\u00e9p\u00e9tez l\u2019\u00e9tape 2."
        ),
        "flash_guide.step4_title": "\u00c9tape 4 : Installer le firmware",
        "flash_guide.step4_text": (
            "Glissez-d\u00e9posez le fichier .uf2 dans le lecteur RPI-RP2.\n"
            "Le clavier red\u00e9marre automatiquement.\n\n"
            "Votre clavier est pr\u00eat ! Configurez les layers sur vial.rocks"
        ),
        # Dialogue configuration Vial-QMK
        "vial_setup.title": "Initialisation de l\u2019environnement",
        "vial_setup.downloading": "T\u00e9l\u00e9chargement de Vial-QMK\u2026",
        "vial_setup.ready": "Vial-QMK pr\u00eat.",
        "vial_setup.error_title": "Erreur de t\u00e9l\u00e9chargement",
        # Dialogues
        "dlg.error": "Erreur",
        "dlg.save_error": "Impossible de sauvegarder : {e}",
        "dlg.load_error": "Impossible de charger le projet : {e}",
        "dlg.vial_unavailable": "Vial-QMK non disponible",
        "dlg.vial_unavailable_msg": (
            "La configuration de Vial-QMK a \u00e9chou\u00e9 ou a \u00e9t\u00e9 annul\u00e9e.\n"
            "L\u2019onglet Build ne fonctionnera pas correctement.\n"
            "Relancez l\u2019application pour r\u00e9essayer."
        ),
        "dlg.lang_change_title": "Langue modifi\u00e9e",
        "dlg.lang_change_msg": "La langue sera appliqu\u00e9e au prochain d\u00e9marrage.",
        "dlg.save_title": "Sauvegarder le projet",
        "dlg.open_title": "Ouvrir un projet",
        "dlg.file_filter": "Projet KFM (*.kfm.json)",
        # Éditeur de clavier custom
        "hardware.custom_btn": "Créer clavier custom\u2026",
        "keyboard_editor.title": "Éditeur de clavier custom",
        "keyboard_editor.name_label": "Nom du clavier (slug) :",
        "keyboard_editor.base_label": "Partir d\u2019un clavier existant :",
        "keyboard_editor.base_empty": "\u2014 Canvas vide \u2014",
        "keyboard_editor.split_label": "Clavier split (deux moitiés) :",
        "keyboard_editor.import_pcb": "Importer image PCB\u2026",
        "keyboard_editor.snap_grid": "Snap to grid",
        "keyboard_editor.add_key": "Ajouter touche",
        "keyboard_editor.delete_key": "Supprimer sélection",
        "keyboard_editor.save": "Sauvegarder",
        "keyboard_editor.cancel": "Annuler",
        "keyboard_editor.section_mcu": "Microcontrôleur",
        "keyboard_editor.section_caps": "Capacités",
        "keyboard_editor.section_pins": "Broches GPIO (avancé)",
        "keyboard_editor.mcu_preset": "MCU existant :",
        "keyboard_editor.mcu_manual": "— saisir manuellement —",
        "keyboard_editor.mcu_preset": "Existing MCU:",
        "keyboard_editor.mcu_manual": "— enter manually —",
        "keyboard_editor.mcu_id": "Identifiant MCU :",
        "keyboard_editor.mcu_name": "Nom affiché :",
        "keyboard_editor.mcu_boot": "Bootloader :",
        "keyboard_editor.oled": "OLED :",
        "keyboard_editor.rgb": "RGB :",
        "keyboard_editor.encoder": "Encodeur :",
        "keyboard_editor.pins_rows": "Pins lignes (matrix_rows) :",
        "keyboard_editor.pins_cols": "Pins colonnes (matrix_cols) :",
        "keyboard_editor.pins_serial": "Broche serial TX :",
        "keyboard_editor.pins_ws2812": "Broche WS2812 :",
        "keyboard_editor.pins_warning": "Pins incorrects = firmware muet. Modifiez uniquement si vous connaissez votre PCB.",
        "keyboard_editor.err_empty_name": "Le nom ne peut pas être vide.",
        "keyboard_editor.err_invalid_name": "Le nom doit contenir uniquement des lettres minuscules, chiffres et tirets.",
        "keyboard_editor.err_name_exists": "Un clavier avec ce nom existe déjà.",
        "keyboard_editor.err_no_keys": "Ajoutez au moins une touche avant de sauvegarder.",
        "keyboard_editor.key_props_title": "Propriétés de la touche",
        "keyboard_editor.key_row": "Ligne matrice (row) :",
        "keyboard_editor.key_col": "Colonne matrice (col) :",
        "keyboard_editor.key_w": "Largeur (U) :",
        "keyboard_editor.key_r": "Rotation (°) :",
        "keyboard_editor.mirror_btn": "Miroir G→D",
        "keyboard_editor.split_clear_warning": "Décocher 'split' va supprimer toutes les touches de la moitié droite. Continuer ?",
        "keyboard_editor.pcb_duplicate_title": "Dupliquer l'image PCB",
        "keyboard_editor.pcb_duplicate_msg": "Clavier split détecté. Dupliquer l'image en miroir pour la moitié droite ?",
        "keyboard_editor.delete_image": "Supprimer image(s)",
        "keyboard_editor.indicator_oled_left": "OLED G",
        "keyboard_editor.indicator_oled_right": "OLED D",
        "keyboard_editor.indicator_encoder": "ENC",
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
        # Generic buttons
        "btn.close": "Close",
        "btn.previous": "Previous",
        "btn.next": "Next",
        # Hardware tab
        "hardware.keyboard_model": "Keyboard model:",
        "hardware.mcu": "Microcontroller:",
        "hardware.layout_variant": "Layout variant:",
        "hardware.oled": "OLED screens:",
        "hardware.rgb": "RGB (underglow / per-key):",
        "hardware.oled.none": "None",
        "hardware.oled.left_only": "Left only",
        "hardware.oled.right_only": "Right only",
        "hardware.oled.both": "Left and right",
        # OLED tab
        "oled.side.left": "Left",
        "oled.side.right": "Right",
        "oled.import_btn": "Import image\u2026",
        "oled.group.utils": "Utilities",
        "oled.group.eyecandy": "Eye Candy",
        "oled.overlay.layer": "Layer",
        "oled.overlay.caps_lock": "Caps Lock",
        "oled.overlay.wpm": "WPM",
        "oled.overlay.rgb_mode": "RGB animation",
        "oled.overlay.kfm": "<KFM>\u2122",
        "oled.overlay.katawajojo": "KatawaJojo",
        "oled.overlay.luna": "Luna",
        "oled.overlay.ocean_dream": "Ocean Dream",
        "oled.overlay.bongo": "Bongo Cat",
        "oled.overlay.crab": "Crab",
        "oled.btn.negative": "Invert",
        "oled.btn.rotate": "Rotate 90\u00b0",
        "oled.btn.reset": "Reset screen",
        "oled.anti_burnin": "Anti burn-in (invert 1\u00a0s / minute)",
        "oled.sleep": "Sleep mode (screens + lights)",
        "oled.sleep_timeout": "Inactivity delay (s):",
        "oled.import_dialog_title": "Import an image",
        "oled.image_filter": "Images (*.png *.bmp *.gif)",
        "oled.import_error_title": "Import error",
        "oled.import_error_msg": "Cannot load image: {msg}",
        # Build tab
        "build.btn.generate": "Generate firmware",
        "build.btn.export": "Export firmware",
        "build.btn.guide": "Flash guide",
        "build.toolchain_found": "Toolchain: {gcc_path}  |  version {version}  |  source: {source}",
        "build.toolchain_not_found": "\u26a0 Toolchain not found\n{msg}",
        "build.toolchain_missing_title": "Toolchain not found",
        "build.vial_not_init_title": "Vial-QMK not initialised",
        "build.vial_not_init_msg": (
            "Vial-QMK is not available in the cache.\n"
            "Restart the application to download it."
        ),
        "build.compiling": "Compiling\u2026",
        "build.firmware_size": "Firmware: {size_kb} KB / {flash_kb} KB used",
        "build.oversized_title": "Firmware too large",
        "build.oversized_msg": (
            "The firmware ({size_kb} KB) exceeds the flash capacity of MCU "
            "{mcu} ({flash_kb} KB).\n"
            "Reduce enabled features before flashing."
        ),
        "build.success": "Build successful.",
        "build.error": "Build failed.",
        "build.error_title": "Build error",
        "build.file_not_found_title": "File not found",
        "build.file_not_found_msg": (
            "The firmware file is no longer available.\n"
            "Run a build before exporting."
        ),
        "build.export_dialog_title": "Export firmware",
        "build.uf2_filter": "UF2 firmware (*.uf2)",
        "build.export_error_title": "Export error",
        "build.export_error_msg": "Cannot export firmware:\n{exc}",
        "build.export_success_title": "Export successful",
        "build.export_success_msg": "Firmware exported to:\n{dest}",
        # About dialog
        "about.title": "About \u2014 keyboard_firmware_maker {version}",
        "about.version": "Version: {version}",
        "about.description": (
            "Desktop application to create and customise\n"
            "QMK/Vial-QMK firmware for split mechanical keyboards."
        ),
        # Flash guide dialog
        "flash_guide.title": "Firmware flash guide",
        "flash_guide.progress": "Step {current} / {total}",
        "flash_guide.missing_image": "[missing image: {name}]",
        "flash_guide.step1_title": "Step 1: Locate the BOOT button",
        "flash_guide.step1_text": (
            "On your Sofle PCB, find the button labelled BOOT\n"
            "(usually near the RP2040 microcontroller)."
        ),
        "flash_guide.step2_title": "Step 2: Enter bootloader mode",
        "flash_guide.step2_text": (
            "1. Hold the BOOT button\n"
            "2. Plug the USB cable into your keyboard\n"
            "3. Release the BOOT button"
        ),
        "flash_guide.step3_title": "Step 3: RPI-RP2 drive detected",
        "flash_guide.step3_text": (
            "A drive named \u2018RPI-RP2\u2019 appears in your file explorer.\n"
            "If it does not appear, repeat step 2."
        ),
        "flash_guide.step4_title": "Step 4: Install the firmware",
        "flash_guide.step4_text": (
            "Drag and drop the .uf2 file onto the RPI-RP2 drive.\n"
            "The keyboard restarts automatically.\n\n"
            "Your keyboard is ready! Configure the layers at vial.rocks"
        ),
        # Vial-QMK setup dialog
        "vial_setup.title": "Environment setup",
        "vial_setup.downloading": "Downloading Vial-QMK\u2026",
        "vial_setup.ready": "Vial-QMK ready.",
        "vial_setup.error_title": "Download error",
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
        # Custom keyboard editor
        "hardware.custom_btn": "Create custom keyboard\u2026",
        "keyboard_editor.title": "Custom keyboard editor",
        "keyboard_editor.name_label": "Keyboard name (slug):",
        "keyboard_editor.base_label": "Start from existing keyboard:",
        "keyboard_editor.base_empty": "\u2014 Empty canvas \u2014",
        "keyboard_editor.split_label": "Split keyboard (two halves):",
        "keyboard_editor.import_pcb": "Import PCB image\u2026",
        "keyboard_editor.snap_grid": "Snap to grid",
        "keyboard_editor.add_key": "Add key",
        "keyboard_editor.delete_key": "Delete selection",
        "keyboard_editor.save": "Save",
        "keyboard_editor.cancel": "Cancel",
        "keyboard_editor.section_mcu": "Microcontroller",
        "keyboard_editor.section_caps": "Capabilities",
        "keyboard_editor.section_pins": "GPIO pins (advanced)",
        "keyboard_editor.mcu_preset": "Existing MCU:",
        "keyboard_editor.mcu_manual": "— enter manually —",
        "keyboard_editor.mcu_id": "MCU identifier:",
        "keyboard_editor.mcu_name": "Display name:",
        "keyboard_editor.mcu_boot": "Bootloader:",
        "keyboard_editor.oled": "OLED:",
        "keyboard_editor.rgb": "RGB:",
        "keyboard_editor.encoder": "Encoder:",
        "keyboard_editor.pins_rows": "Row pins (matrix_rows):",
        "keyboard_editor.pins_cols": "Column pins (matrix_cols):",
        "keyboard_editor.pins_serial": "Serial TX pin:",
        "keyboard_editor.pins_ws2812": "WS2812 pin:",
        "keyboard_editor.pins_warning": "Wrong pins = silent firmware. Only modify if you know your PCB.",
        "keyboard_editor.err_empty_name": "Name cannot be empty.",
        "keyboard_editor.err_invalid_name": "Name must contain only lowercase letters, digits and hyphens.",
        "keyboard_editor.err_name_exists": "A keyboard with this name already exists.",
        "keyboard_editor.err_no_keys": "Add at least one key before saving.",
        "keyboard_editor.key_props_title": "Key properties",
        "keyboard_editor.key_row": "Matrix row:",
        "keyboard_editor.key_col": "Matrix column:",
        "keyboard_editor.key_w": "Width (U):",
        "keyboard_editor.key_r": "Rotation (°):",
        "keyboard_editor.mirror_btn": "Mirror L→R",
        "keyboard_editor.split_clear_warning": "Unchecking 'split' will delete all keys on the right half. Continue?",
        "keyboard_editor.pcb_duplicate_title": "Duplicate PCB image",
        "keyboard_editor.pcb_duplicate_msg": "Split keyboard detected. Mirror the PCB image for the right half?",
        "keyboard_editor.delete_image": "Delete image(s)",
        "keyboard_editor.indicator_oled_left": "OLED L",
        "keyboard_editor.indicator_oled_right": "OLED R",
        "keyboard_editor.indicator_encoder": "ENC",
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
        # Pulsanti generici
        "btn.close": "Chiudi",
        "btn.previous": "Precedente",
        "btn.next": "Avanti",
        # Scheda Hardware
        "hardware.keyboard_model": "Modello tastiera:",
        "hardware.mcu": "Microcontrollore:",
        "hardware.layout_variant": "Variante layout:",
        "hardware.oled": "Schermi OLED:",
        "hardware.rgb": "RGB (underglow / per-key):",
        "hardware.oled.none": "Nessuno",
        "hardware.oled.left_only": "Solo sinistra",
        "hardware.oled.right_only": "Solo destra",
        "hardware.oled.both": "Sinistra e destra",
        # Scheda OLED
        "oled.side.left": "Sinistra",
        "oled.side.right": "Destra",
        "oled.import_btn": "Importa immagine\u2026",
        "oled.group.utils": "Utilità",
        "oled.group.eyecandy": "Eye Candy",
        "oled.overlay.layer": "Layer",
        "oled.overlay.caps_lock": "Caps Lock",
        "oled.overlay.wpm": "WPM",
        "oled.overlay.rgb_mode": "Animazione RGB",
        "oled.overlay.kfm": "<KFM>\u2122",
        "oled.overlay.katawajojo": "KatawaJojo",
        "oled.overlay.luna": "Luna",
        "oled.overlay.ocean_dream": "Ocean Dream",
        "oled.overlay.bongo": "Bongo Cat",
        "oled.overlay.crab": "Granchio",
        "oled.btn.negative": "Negativo",
        "oled.btn.rotate": "Rotazione 90\u00b0",
        "oled.btn.reset": "Ripristina schermo",
        "oled.anti_burnin": "Anti-marcatura (inversione 1\u00a0s / minuto)",
        "oled.sleep": "Modalità standby (schermi + luci)",
        "oled.sleep_timeout": "Ritardo inattività (s):",
        "oled.import_dialog_title": "Importa un\u2019immagine",
        "oled.image_filter": "Immagini (*.png *.bmp *.gif)",
        "oled.import_error_title": "Errore di importazione",
        "oled.import_error_msg": "Impossibile caricare l\u2019immagine: {msg}",
        # Scheda Build
        "build.btn.generate": "Genera firmware",
        "build.btn.export": "Esporta firmware",
        "build.btn.guide": "Guida flash",
        "build.toolchain_found": "Toolchain: {gcc_path}  |  versione {version}  |  sorgente: {source}",
        "build.toolchain_not_found": "\u26a0 Toolchain non trovata\n{msg}",
        "build.toolchain_missing_title": "Toolchain non trovata",
        "build.vial_not_init_title": "Vial-QMK non inizializzato",
        "build.vial_not_init_msg": (
            "Vial-QMK non \u00e8 disponibile nella cache.\n"
            "Riavvia l\u2019applicazione per scaricarlo."
        ),
        "build.compiling": "Compilazione in corso\u2026",
        "build.firmware_size": "Firmware: {size_kb} KB / {flash_kb} KB utilizzati",
        "build.oversized_title": "Firmware troppo grande",
        "build.oversized_msg": (
            "Il firmware ({size_kb} KB) supera la capacit\u00e0 flash dell\u2019MCU "
            "{mcu} ({flash_kb} KB).\n"
            "Riduci le funzionalit\u00e0 attivate prima di flashare."
        ),
        "build.success": "Compilazione completata.",
        "build.error": "Compilazione fallita.",
        "build.error_title": "Errore di compilazione",
        "build.file_not_found_title": "File non trovato",
        "build.file_not_found_msg": (
            "Il file firmware non \u00e8 pi\u00f9 disponibile.\n"
            "Riesegui una compilazione prima di esportare."
        ),
        "build.export_dialog_title": "Esporta firmware",
        "build.uf2_filter": "Firmware UF2 (*.uf2)",
        "build.export_error_title": "Errore di esportazione",
        "build.export_error_msg": "Impossibile esportare il firmware:\n{exc}",
        "build.export_success_title": "Esportazione riuscita",
        "build.export_success_msg": "Firmware esportato in:\n{dest}",
        # Dialogo Informazioni
        "about.title": "Informazioni \u2014 keyboard_firmware_maker {version}",
        "about.version": "Versione: {version}",
        "about.description": (
            "Applicazione desktop per creare e personalizzare firmware\n"
            "QMK/Vial-QMK per tastiere meccaniche split."
        ),
        # Dialogo guida flash
        "flash_guide.title": "Guida flash firmware",
        "flash_guide.progress": "Passaggio {current} / {total}",
        "flash_guide.missing_image": "[immagine mancante: {name}]",
        "flash_guide.step1_title": "Passo 1: Individuare il pulsante BOOT",
        "flash_guide.step1_text": (
            "Sul PCB del Sofle, individua il pulsante BOOT\n"
            "(di solito vicino al microcontrollore RP2040)."
        ),
        "flash_guide.step2_title": "Passo 2: Entrare in modalit\u00e0 bootloader",
        "flash_guide.step2_text": (
            "1. Tieni premuto il pulsante BOOT\n"
            "2. Collega il cavo USB alla tastiera\n"
            "3. Rilascia il pulsante BOOT"
        ),
        "flash_guide.step3_title": "Passo 3: Lettore RPI-RP2 rilevato",
        "flash_guide.step3_text": (
            "Un lettore chiamato \u2018RPI-RP2\u2019 appare nel file manager.\n"
            "Se non appare, ripeti il passo 2."
        ),
        "flash_guide.step4_title": "Passo 4: Installare il firmware",
        "flash_guide.step4_text": (
            "Trascina il file .uf2 nel lettore RPI-RP2.\n"
            "La tastiera si riavvia automaticamente.\n\n"
            "La tua tastiera \u00e8 pronta! Configura i layer su vial.rocks"
        ),
        # Dialogo setup Vial-QMK
        "vial_setup.title": "Inizializzazione dell\u2019ambiente",
        "vial_setup.downloading": "Download di Vial-QMK\u2026",
        "vial_setup.ready": "Vial-QMK pronto.",
        "vial_setup.error_title": "Errore di download",
        # Dialoghi
        "dlg.error": "Errore",
        "dlg.save_error": "Impossibile salvare: {e}",
        "dlg.load_error": "Impossibile caricare il progetto: {e}",
        "dlg.vial_unavailable": "Vial-QMK non disponibile",
        "dlg.vial_unavailable_msg": (
            "La configurazione di Vial-QMK \u00e8 fallita o \u00e8 stata annullata.\n"
            "La scheda Build non funzioner\u00e0 correttamente.\n"
            "Riavvia l\u2019applicazione per riprovare."
        ),
        "dlg.lang_change_title": "Lingua modificata",
        "dlg.lang_change_msg": "La lingua sar\u00e0 applicata al prossimo avvio.",
        "dlg.save_title": "Salva progetto",
        "dlg.open_title": "Apri progetto",
        "dlg.file_filter": "Progetto KFM (*.kfm.json)",
        # Editor tastiera custom
        "hardware.custom_btn": "Crea tastiera custom\u2026",
        "keyboard_editor.title": "Editor tastiera custom",
        "keyboard_editor.name_label": "Nome tastiera (slug):",
        "keyboard_editor.base_label": "Parti da una tastiera esistente:",
        "keyboard_editor.base_empty": "\u2014 Canvas vuoto \u2014",
        "keyboard_editor.split_label": "Tastiera split (due metà):",
        "keyboard_editor.import_pcb": "Importa immagine PCB\u2026",
        "keyboard_editor.snap_grid": "Snap to grid",
        "keyboard_editor.add_key": "Aggiungi tasto",
        "keyboard_editor.delete_key": "Elimina selezione",
        "keyboard_editor.save": "Salva",
        "keyboard_editor.cancel": "Annulla",
        "keyboard_editor.section_mcu": "Microcontrollore",
        "keyboard_editor.section_caps": "Capacità",
        "keyboard_editor.section_pins": "Pin GPIO (avanzato)",
        "keyboard_editor.mcu_preset": "MCU esistente:",
        "keyboard_editor.mcu_manual": "— inserire manualmente —",
        "keyboard_editor.mcu_id": "Identificatore MCU:",
        "keyboard_editor.mcu_name": "Nome visualizzato:",
        "keyboard_editor.mcu_boot": "Bootloader:",
        "keyboard_editor.oled": "OLED:",
        "keyboard_editor.rgb": "RGB:",
        "keyboard_editor.encoder": "Encoder:",
        "keyboard_editor.pins_rows": "Pin righe (matrix_rows):",
        "keyboard_editor.pins_cols": "Pin colonne (matrix_cols):",
        "keyboard_editor.pins_serial": "Pin serial TX:",
        "keyboard_editor.pins_ws2812": "Pin WS2812:",
        "keyboard_editor.pins_warning": "Pin errati = firmware muto. Modifica solo se conosci il tuo PCB.",
        "keyboard_editor.err_empty_name": "Il nome non può essere vuoto.",
        "keyboard_editor.err_invalid_name": "Il nome deve contenere solo lettere minuscole, cifre e trattini.",
        "keyboard_editor.err_name_exists": "Esiste già una tastiera con questo nome.",
        "keyboard_editor.err_no_keys": "Aggiungi almeno un tasto prima di salvare.",
        "keyboard_editor.key_props_title": "Proprietà del tasto",
        "keyboard_editor.key_row": "Riga matrice (row):",
        "keyboard_editor.key_col": "Colonna matrice (col):",
        "keyboard_editor.key_w": "Larghezza (U):",
        "keyboard_editor.key_r": "Rotazione (°):",
        "keyboard_editor.mirror_btn": "Specchio S→D",
        "keyboard_editor.split_clear_warning": "Deselezionare 'split' eliminerà tutti i tasti della metà destra. Continuare?",
        "keyboard_editor.pcb_duplicate_title": "Duplica immagine PCB",
        "keyboard_editor.pcb_duplicate_msg": "Tastiera split rilevata. Specchiare l'immagine PCB per la metà destra?",
        "keyboard_editor.delete_image": "Elimina immagine/i",
        "keyboard_editor.indicator_oled_left": "OLED S",
        "keyboard_editor.indicator_oled_right": "OLED D",
        "keyboard_editor.indicator_encoder": "ENC",
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
    },
}
