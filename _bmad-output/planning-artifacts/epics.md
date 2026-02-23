---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-epic-1', 'step-03-epic-2', 'step-03-epic-3', 'step-03-epic-4', 'step-04-final-validation']
status: 'complete'
completedAt: '2026-02-22'
epic_count: 4
story_count: 14
fr_coverage: '33/33'
nfr_coverage: '15/15'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# keyboard_firmware_maker - Epic Breakdown

## Overview

Ce document fournit le découpage complet en épics et stories pour keyboard_firmware_maker, décomposant les exigences du PRD et les décisions d'architecture en stories implémentables.

## Requirements Inventory

### Functional Requirements

FR1: L'utilisateur peut sélectionner son modèle de clavier parmi une liste intégrée (Sofle 2.1 RGB, Corne, Lily58)
FR2: L'utilisateur peut sélectionner le microcontrôleur de son clavier (RP2040, Pro Micro, Elite-C)
FR3: Le système détecte automatiquement les capacités du clavier sélectionné (présence OLED, présence RGB)
FR4: Le système masque dynamiquement les sections non applicables au clavier sélectionné (ex : onglet RGB masqué si pas de LEDs)
FR5: L'utilisateur peut consulter une aide contextuelle décrivant chaque modèle de clavier et microcontrôleur
FR6: L'utilisateur peut importer un fichier GIF, PNG ou BMP comme contenu à afficher sur l'écran OLED
FR7: Le système convertit automatiquement l'image ou GIF importé en bitmap 1-bit 64×128 pixels
FR8: L'utilisateur peut prévisualiser le rendu OLED pixel-perfect dans l'application avant génération du firmware
FR9: Le système affiche les frames d'un GIF importé en prévisualisation animée dans l'application
FR10: L'utilisateur peut configurer l'affichage d'informations système sur l'OLED (layer actif, état Caps Lock, WPM)
FR11: L'utilisateur peut assigner une couleur spécifique à une ou plusieurs touches individuelles via une interface visuelle
FR12: L'utilisateur peut sélectionner un effet RGB prédéfini parmi une liste (couleur statique uniforme, ripple au keystroke)
FR13: L'utilisateur peut configurer les paramètres d'un effet ripple (couleur de la touche pressée, couleur des touches voisines, vitesse de fondu)
FR14: L'utilisateur peut assigner des effets RGB déclenchés par des touches spécifiques
FR15: L'utilisateur peut prévisualiser un aperçu animé des effets RGB configurés dans l'application
FR16: Le système compile la configuration utilisateur en firmware Vial-QMK compatible
FR17: Le système vérifie que la taille du firmware compilé respecte la capacité flash du microcontrôleur cible
FR18: Le système avertit l'utilisateur si la taille du firmware dépasse la capacité mémoire du MCU sélectionné
FR19: Le système produit un fichier .uf2 valide prêt à être flashé
FR20: Le système affiche la progression de la compilation en temps réel
FR21: Le système affiche les erreurs de compilation de manière lisible (messages humanisés, pas de logs QMK bruts)
FR22: Le système propose un diagnostic d'erreur simplifié lorsque la cause de l'échec est identifiable
FR23: Le système fournit un guide de flash illustré intégré (procédure mode bootloader, étapes de glisser-déposer du .uf2)
FR24: Le firmware généré est compatible avec vial.rocks pour la configuration des layers et keymaps
FR25: L'utilisateur peut sauvegarder sa configuration en cours dans un fichier projet local
FR26: L'utilisateur peut recharger un projet précédemment sauvegardé
FR27: L'utilisateur peut modifier une configuration existante et regénérer le firmware sans repartir de zéro
FR28: L'utilisateur peut exporter le fichier .uf2 généré vers l'emplacement de son choix sur son système de fichiers
FR29: L'application fonctionne sans connexion réseau (mode offline complet — aucune fonctionnalité ne nécessite Internet)
FR30: L'application fonctionne sans droits administrateur
FR31: L'application affiche sa version courante dans une section "À propos"
FR32: L'application s'exécute sans installation de dépendances externes, ou fournit des instructions d'installation claires directement dans l'interface
FR33: L'utilisateur peut accéder aux guides d'utilisation et à la documentation de flash depuis l'application

### NonFunctional Requirements

NFR1: La compilation du firmware s'exécute en moins de 2 minutes sur une machine standard (x64 moderne, 4 Go RAM)
NFR2: Les interactions UI (sélection de touche, changement de couleur, navigation entre onglets) répondent en moins de 200ms
NFR3: La prévisualisation OLED se met à jour en moins de 500ms après import ou modification d'un asset
NFR4: Le démarrage de l'application s'effectue en moins de 5 secondes sur une machine standard
NFR5: L'application ne plante pas durant un workflow de génération complet (de la sélection du clavier à l'export du .uf2)
NFR6: Tout fichier .uf2 produit par l'application est syntaxiquement valide (conforme au format UF2 Microsoft)
NFR7: La sauvegarde d'un projet ne corrompra pas un fichier projet existant (écriture atomique)
NFR8: Un échec de compilation ne laisse pas l'application dans un état bloqué — l'utilisateur peut corriger et relancer sans redémarrer
NFR9: L'application fonctionne sur Windows 10 et Windows 11 (x64)
NFR10: L'application fonctionne sur les distributions Linux majeures avec glibc ≥ 2.31 (Ubuntu 20.04+, Debian 11+, Fedora 33+)
NFR11: L'AppImage Linux fonctionne sans installation de paquets supplémentaires sur les distributions cibles
NFR12: Le firmware généré est compatible avec les versions stables de Vial-QMK supportant le RP2040
NFR13: Les définitions de claviers sont stockées dans des fichiers YAML séparés — l'ajout d'un nouveau modèle ne nécessite pas de modifier le code source
NFR14: Le code source est documenté suffisamment pour qu'un développeur tiers puisse comprendre l'architecture et contribuer sans assistance
NFR15: La toolchain QMK embarquée est versionnée explicitement — une mise à jour de Vial-QMK ne casse pas silencieusement les firmwares générés

### Additional Requirements

**De l'Architecture :**
- Pas de starter template — projet initialisé avec pyproject.toml + structure modulaire Python 3.11 + PySide6 6.10.2 (Story 1.1)
- Dépendances : PySide6, Pillow, NumPy, Jinja2, PyInstaller, pytest, pytest-qt
- QThread obligatoire pour toute opération > 50ms (compilation, conversion image, git clone)
- Séparation stricte widget.py / processor.py dans chaque module domaine
- ProjectModel injecté via constructeur (jamais de singleton global)
- Écriture atomique pour tous les fichiers projet (tmp + replace)
- Vial-QMK téléchargé au premier lancement, mis en cache dans `~/.keyboard_firmware_maker/vial-qmk/` (dialog de progression requis)
- Toolchain arm-none-eabi-gcc vendorée dans `toolchain/windows/` et `toolchain/linux/` avec fallback détection système
- Génération code QMK via templates Jinja2 (`.c.j2`, `.h.j2`) paramétrés depuis ProjectModel
- Résolution des chemins via `sys._MEIPASS` pour les bundles PyInstaller
- CI/CD : GitHub Actions matrix build (Windows + Linux) déclenché sur tag `v*.*.*`
- Logging via stdlib logging uniquement (`logging.getLogger(__name__)`), aucun print()
- Format projet JSON (clés snake_case, couleurs hex `#RRGGBB`, chemins absolus)

**Pas de document UX (non applicable — pas de guide de design UX produit)**

### FR Coverage Map

FR1: Epic 1 — Sélection du modèle de clavier (liste intégrée)
FR2: Epic 1 — Sélection du microcontrôleur
FR3: Epic 1 — Détection automatique des capacités (OLED, RGB)
FR4: Epic 1 — Masquage dynamique des sections non applicables
FR5: Epic 1 — Aide contextuelle matériel (info-bulles)
FR6: Epic 2 — Import fichier GIF/PNG/BMP
FR7: Epic 2 — Conversion automatique 1-bit 64×128px
FR8: Epic 2 — Prévisualisation OLED pixel-perfect
FR9: Epic 2 — Prévisualisation animée GIF frame par frame
FR10: Epic 2 — Configuration overlays infos système (layer, Caps Lock, WPM)
FR11: Epic 3 — Assignation couleur par touche (interface visuelle)
FR12: Epic 3 — Sélection effet RGB prédéfini (statique, ripple)
FR13: Epic 3 — Paramétrage effet ripple (couleurs, vitesse fondu)
FR14: Epic 3 — Effets RGB déclenchés par touches spécifiques
FR15: Epic 3 — Aperçu animé des effets RGB configurés
FR16: Epic 4 — Compilation configuration en firmware Vial-QMK
FR17: Epic 4 — Vérification taille firmware vs capacité flash MCU
FR18: Epic 4 — Avertissement si dépassement capacité mémoire MCU
FR19: Epic 4 — Production fichier .uf2 valide
FR20: Epic 4 — Progression compilation en temps réel
FR21: Epic 4 — Erreurs de compilation lisibles (messages humanisés)
FR22: Epic 4 — Diagnostic d'erreur simplifié
FR23: Epic 4 — Guide de flash illustré intégré
FR24: Epic 4 — Compatibilité firmware avec vial.rocks
FR25: Epic 1 — Sauvegarde configuration dans fichier projet local
FR26: Epic 1 — Rechargement projet précédemment sauvegardé
FR27: Epic 1 — Modification configuration existante sans repartir de zéro
FR28: Epic 4 — Export fichier .uf2 vers emplacement choisi par l'utilisateur
FR29: Epic 1 — Fonctionnement offline complet (aucun appel réseau)
FR30: Epic 1 — Fonctionnement sans droits administrateur
FR31: Epic 1 — Affichage version courante dans dialogue "À propos"
FR32: Epic 4 — Toolchain embarquée ou instructions d'installation claires
FR33: Epic 4 — Accès aux guides depuis l'application

## Epic List

### Epic 1: Application Foundation & Sélection Matériel
L'utilisateur peut ouvrir l'application, sélectionner son modèle de clavier et son microcontrôleur, voir les capacités disponibles (OLED/RGB) avec masquage dynamique des sections non applicables, et sauvegarder/recharger sa configuration de projet. L'application fonctionne entièrement offline, sans droits administrateur.
**FRs couverts :** FR1, FR2, FR3, FR4, FR5, FR25, FR26, FR27, FR29, FR30, FR31

### Epic 2: Personnalisation OLED
L'utilisateur peut importer une image ou un GIF, voir une prévisualisation pixel-perfect 64×128px en 1-bit noir et blanc (avec animation frame par frame pour les GIF), et configurer l'affichage d'informations système sur l'écran OLED (layer actif, Caps Lock, WPM).
**FRs couverts :** FR6, FR7, FR8, FR9, FR10

### Epic 3: Personnalisation RGB
L'utilisateur peut assigner des couleurs spécifiques aux touches via une interface visuelle, sélectionner et configurer des effets RGB prédéfinis (couleur statique, ripple au keystroke avec paramètres personnalisables), et prévisualiser les effets configurés dans une animation en temps réel.
**FRs couverts :** FR11, FR12, FR13, FR14, FR15

### Epic 4: Génération Firmware & Distribution
L'utilisateur peut compiler un firmware Vial-QMK complet depuis sa configuration, suivre la progression en temps réel, être averti si la taille dépasse la capacité du MCU, obtenir un fichier .uf2 valide, suivre un guide de flash illustré étape par étape, et retrouver son clavier immédiatement configurable via vial.rocks.
**FRs couverts :** FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23, FR24, FR28, FR32, FR33

---

## Epic 1: Application Foundation & Sélection Matériel

L'utilisateur peut ouvrir l'application, sélectionner son modèle de clavier et son microcontrôleur, voir les capacités disponibles (OLED/RGB) avec masquage dynamique des sections non applicables, et sauvegarder/recharger sa configuration de projet. L'application fonctionne entièrement offline, sans droits administrateur.

### Story 1.1: Initialisation du projet et premier lancement

As a développeur (Pentinou),
I want to initialize the project structure and launch a working application skeleton,
So that I have a stable foundation with MainWindow, ProjectModel, and empty module tabs to build upon.

**Acceptance Criteria:**

**Given** je lance `python main.py` depuis le répertoire du projet
**When** l'application démarre
**Then** une QMainWindow apparaît avec 4 onglets : "Matériel", "OLED", "RGB", "Build"
**And** l'application démarre en moins de 5 secondes (NFR4)
**And** aucun droit administrateur n'est requis (FR30)

**Given** l'application est lancée
**When** j'ouvre le menu "À propos"
**Then** la version courante est affichée (ex : "0.1.0") (FR31)
**And** un lien vers le dépôt GitHub est présent

**Given** l'application est lancée sous Windows ou Linux
**When** elle s'exécute depuis le bundle PyInstaller
**Then** elle trouve ses ressources via `sys._MEIPASS` sans erreur de chemin

### Story 1.2: Sélection du clavier et du microcontrôleur

As a utilisateur (Pentinou ou Alex),
I want to select my keyboard model and MCU from the hardware tab,
So that the application knows which keyboard I have and configures the correct firmware target.

**Acceptance Criteria:**

**Given** je suis dans l'onglet "Matériel"
**When** j'ouvre le sélecteur de modèle de clavier
**Then** je vois au minimum : "Sofle 2.1 RGB", "Corne", "Lily58" (FR1)
**And** les définitions sont chargées depuis les fichiers YAML dans `keyboards/`

**Given** j'ai sélectionné un modèle de clavier
**When** je regarde le sélecteur de MCU
**Then** je vois les MCU compatibles avec ce modèle (FR2)
**And** "RP2040" est disponible pour le Sofle 2.1 RGB

**Given** je survole un modèle de clavier ou un MCU
**When** je lis l'info-bulle
**Then** je vois une description contextuelle du matériel (FR5)

**Given** j'ai sélectionné "Sofle 2.1 RGB" et "RP2040"
**When** les sélections sont confirmées
**Then** le ProjectModel est mis à jour : `keyboard.model = "sofle-v2"`, `keyboard.mcu = "rp2040"`

### Story 1.3: Détection des capacités et masquage dynamique

As a utilisateur,
I want the application to automatically show or hide sections based on my keyboard's capabilities,
So that I am not confused by options that don't apply to my hardware.

**Acceptance Criteria:**

**Given** j'ai sélectionné "Sofle 2.1 RGB" (OLED = true, RGB = true dans le YAML)
**When** la sélection est confirmée
**Then** les onglets "OLED" et "RGB" sont activés et visibles (FR3, FR4)

**Given** j'ai sélectionné un clavier sans OLED (`oled: false` dans le YAML)
**When** la sélection est confirmée
**Then** l'onglet "OLED" est désactivé ou masqué

**Given** j'ai sélectionné un clavier sans RGB (`rgb: false` dans le YAML)
**When** la sélection est confirmée
**Then** l'onglet "RGB" est désactivé ou masqué

**Given** je change de modèle de clavier
**When** les capacités du nouveau modèle diffèrent
**Then** les onglets visibles se mettent à jour dynamiquement sans redémarrage de l'application (FR4)

### Story 1.4: Sauvegarde et rechargement de projet

As a utilisateur (Pentinou),
I want to save my configuration and reload it later,
So that I can resume my work without starting from zero after a firmware issue (Parcours 3).

**Acceptance Criteria:**

**Given** j'ai configuré ma sélection de clavier
**When** je clique "Sauvegarder le projet"
**Then** une fenêtre de dialogue s'ouvre pour choisir l'emplacement de sauvegarde
**And** la configuration est sauvegardée en JSON valide avec des clés snake_case (FR25)

**Given** j'ai sélectionné "Sauvegarder" et que le chemin est choisi
**When** l'écriture s'effectue
**Then** elle utilise le pattern atomique (tmp + replace) — le fichier existant n'est jamais corrompu (NFR7)

**Given** un fichier projet existe sur le disque
**When** je clique "Ouvrir un projet" et je le sélectionne
**Then** l'application charge la configuration et restaure la sélection de clavier dans tous les onglets (FR26)

**Given** j'ai chargé un projet et modifié la sélection matériel
**When** je sauvegarde à nouveau
**Then** la nouvelle configuration remplace l'ancienne atomiquement (FR27)

**Given** une erreur d'écriture se produit (disque plein, permissions)
**When** la sauvegarde échoue
**Then** le fichier original est intact
**And** un message d'erreur clair est affiché à l'utilisateur

---

## Epic 2: Personnalisation OLED

L'utilisateur peut importer une image ou un GIF, voir une prévisualisation pixel-perfect 64×128px en 1-bit noir et blanc (avec animation frame par frame pour les GIF), et configurer l'affichage d'informations système sur l'écran OLED (layer actif, Caps Lock, WPM).

### Story 2.1: Import et conversion d'image en bitmap OLED

As a utilisateur (Pentinou ou Alex),
I want to import an image file and see it automatically converted to a 1-bit 64×128px preview,
So that I can verify exactly what will appear on my keyboard's OLED screen before generating firmware.

**Acceptance Criteria:**

**Given** je suis dans l'onglet "OLED"
**When** je clique "Importer une image" et je sélectionne un fichier PNG, BMP ou GIF
**Then** l'application accepte le fichier (FR6)
**And** convertit automatiquement l'image en bitmap 1-bit 64×128px avec dithering Floyd-Steinberg (FR7)

**Given** la conversion est terminée
**When** je regarde la zone de prévisualisation
**Then** j'y vois le rendu exact en noir et blanc 64×128px, sans niveaux de gris (FR8)
**And** la prévisualisation est mise à jour en moins de 500ms après l'import (NFR3)

**Given** j'importe une image dont les dimensions ne sont pas 64×128px
**When** la conversion s'effectue
**Then** l'image est redimensionnée et recadrée automatiquement pour tenir dans 64×128px
**And** aucun message d'erreur n'est affiché si le redimensionnement réussit

**Given** j'importe un fichier non supporté ou corrompu
**When** la lecture échoue
**Then** un message d'erreur lisible est affiché (ex : "Format de fichier non supporté")
**And** l'onglet reste dans un état stable et utilisable

### Story 2.2: Prévisualisation animée d'un GIF

As a utilisateur (Alex),
I want to see my imported GIF animate frame by frame in the OLED preview,
So that I can verify the animation will look correct on my keyboard before compiling.

**Acceptance Criteria:**

**Given** j'ai importé un fichier GIF multi-frames
**When** la conversion est terminée
**Then** la prévisualisation affiche les frames en séquence animée (FR9)
**And** la vitesse d'animation reflète le délai inter-frames du GIF original

**Given** un GIF est en cours d'animation dans la prévisualisation
**When** j'observe chaque frame
**Then** chaque frame est rendue en 1-bit 64×128px avec dithering (cohérent avec Story 2.1)

**Given** j'importe un GIF à frame unique (image statique déguisée en GIF)
**When** la conversion s'effectue
**Then** l'application affiche une prévisualisation statique sans erreur

**Given** les données GIF converties (List[bytes] par frame) sont stockées dans ProjectModel
**When** je sauvegarde le projet
**Then** le chemin source du GIF est sauvegardé dans `oled.image_path`
**And** les frames sont regénérées depuis ce chemin au rechargement

### Story 2.3: Configuration des overlays d'informations système

As a utilisateur (Pentinou),
I want to configure which system information is displayed on the OLED alongside my image,
So that I can see useful data like the active layer, Caps Lock state, or WPM on my keyboard.

**Acceptance Criteria:**

**Given** je suis dans l'onglet "OLED"
**When** je regarde la section "Overlays"
**Then** je vois des cases à cocher pour : "Layer actif", "Caps Lock", "WPM" (FR10)

**Given** je coche "Layer actif"
**When** la configuration est mise à jour
**Then** `oled.overlays` dans le ProjectModel inclut `"layer"`

**Given** j'ai configuré des overlays
**When** je sauvegarde mon projet
**Then** la configuration des overlays est persistée dans le fichier JSON

**Given** je recharge un projet avec des overlays configurés
**When** j'ouvre l'onglet "OLED"
**Then** les cases à cocher reflètent la configuration sauvegardée

**Given** j'ai activé un overlay et importé une image
**When** le firmware sera généré (Epic 4)
**Then** le template Jinja2 inclura à la fois l'image OLED et les overlays activés dans `keymap.c`

---

## Epic 3: Personnalisation RGB

L'utilisateur peut assigner des couleurs spécifiques aux touches via une interface visuelle, sélectionner et configurer des effets RGB prédéfinis (couleur statique, ripple au keystroke avec paramètres personnalisables), et prévisualiser les effets configurés dans une animation en temps réel.

### Story 3.1: Assignation de couleur par touche

As a utilisateur (Pentinou),
I want to assign a specific color to individual keys on a visual keyboard layout,
So that I can create a custom per-key RGB configuration without editing code.

**Acceptance Criteria:**

**Given** je suis dans l'onglet "RGB"
**When** je vois le layout de mon clavier Sofle
**Then** un rendu visuel du split clavier (gauche + droite) est affiché avec toutes les touches représentées

**Given** je clique sur une touche dans le layout visuel
**When** je sélectionne une couleur via le color picker
**Then** la touche change de couleur dans le rendu visuel en moins de 200ms (NFR2, FR11)
**And** la couleur est stockée dans `rgb.per_key` du ProjectModel au format `{"KEY_A": "#FF0000"}`

**Given** j'ai assigné des couleurs à plusieurs touches
**When** je sauvegarde le projet
**Then** toutes les assignations par touche sont persistées dans le fichier JSON

**Given** je recharge un projet avec des couleurs par touche
**When** j'ouvre l'onglet "RGB"
**Then** le layout visuel affiche les couleurs restaurées sur chaque touche

### Story 3.2: Sélection et configuration des effets RGB

As a utilisateur (Pentinou ou Alex),
I want to select a preset RGB effect and configure its parameters,
So that my keyboard has a dynamic lighting effect without needing to write QMK code.

**Acceptance Criteria:**

**Given** je suis dans l'onglet "RGB"
**When** je regarde le sélecteur d'effets
**Then** je vois au minimum : "Couleur statique uniforme", "Ripple au keystroke" (FR12)

**Given** je sélectionne "Couleur statique uniforme"
**When** la sélection est confirmée
**Then** un color picker s'affiche pour choisir la couleur uniforme
**And** `rgb.effects` dans le ProjectModel est mis à jour avec `type: "static"` et la couleur choisie

**Given** je sélectionne "Ripple au keystroke"
**When** la sélection est confirmée
**Then** trois paramètres configurables apparaissent (FR13) :
  - Couleur de la touche pressée (`color_primary`)
  - Couleur des touches voisines (`color_secondary`)
  - Vitesse de fondu en ms (`fade_ms`)

**Given** je configure un effet ripple avec couleur primaire rouge (#FF0000) et secondaire orange (#FF8800)
**When** la configuration est validée
**Then** `rgb.effects[0]` dans le ProjectModel contient `{"type": "ripple", "color_primary": "#FF0000", "color_secondary": "#FF8800", "fade_ms": 500}`

**Given** je veux déclencher un effet ripple sur une touche spécifique
**When** j'active le mode "déclencheur par touche"
**Then** je peux cliquer une touche dans le layout visuel pour la désigner comme déclencheur (FR14)
**And** `trigger_key` dans l'effet est mis à jour avec le code de la touche sélectionnée

### Story 3.3: Aperçu animé des effets RGB

As a utilisateur (Pentinou ou Alex),
I want to see an animated preview of my configured RGB effect in the application,
So that I can validate the visual result before compiling and flashing firmware.

**Acceptance Criteria:**

**Given** j'ai sélectionné et configuré un effet RGB
**When** je regarde la zone de prévisualisation
**Then** un aperçu animé de l'effet s'exécute sur le layout visuel du clavier (FR15)

**Given** l'effet "Ripple au keystroke" est configuré
**When** l'aperçu s'affiche
**Then** une animation montre une touche simulée pressée, avec propagation des couleurs primaire → secondaire → fondu vers les touches voisines

**Given** l'effet "Couleur statique uniforme" est configuré
**When** l'aperçu s'affiche
**Then** toutes les touches s'affichent avec la couleur choisie (pas d'animation nécessaire)

**Given** je modifie un paramètre d'effet (ex : changer la couleur secondaire)
**When** la modification est appliquée
**Then** l'aperçu se met à jour en moins de 200ms pour refléter le changement (NFR2)

**Given** l'aperçu utilise un QTimer pour l'animation
**When** je navigue vers un autre onglet
**Then** l'animation se met en pause (le timer s'arrête) pour économiser les ressources

---

## Epic 4: Génération Firmware & Distribution

L'utilisateur peut compiler un firmware Vial-QMK complet depuis sa configuration, suivre la progression en temps réel, être averti si la taille dépasse la capacité du MCU, obtenir un fichier .uf2 valide, suivre un guide de flash illustré étape par étape, et retrouver son clavier immédiatement configurable via vial.rocks.

### Story 4.1: Configuration de l'environnement de build

As a utilisateur (Pentinou ou Alex),
I want the application to automatically set up the build toolchain and Vial-QMK source on first launch,
So that I can compile firmware without installing anything manually.

**Acceptance Criteria:**

**Given** je lance l'application pour la première fois
**When** le cache Vial-QMK n'existe pas dans `~/.keyboard_firmware_maker/vial-qmk/`
**Then** un dialogue de progression s'affiche et télécharge Vial-QMK (version SHA verrouillée) automatiquement

**Given** le téléchargement de Vial-QMK est en cours
**When** je regarde le dialogue
**Then** je vois une barre de progression et un message d'état clair (ex : "Téléchargement de Vial-QMK…")

**Given** le cache Vial-QMK existe déjà
**When** je lance l'application
**Then** aucun téléchargement n'est déclenché — l'app démarre directement (FR29 — offline après init)

**Given** je clique "Générer firmware" dans l'onglet "Build"
**When** la détection de la toolchain s'effectue
**Then** l'application utilise `arm-none-eabi-gcc` vendoré dans `toolchain/{platform}/bin/` (FR32)

**Given** les binaires vendorés sont absents ou incompatibles
**When** la détection de fallback s'effectue
**Then** l'application détecte `arm-none-eabi-gcc` sur le PATH système
**And** si absent, un message clair guide l'utilisateur vers l'installation manuelle (FR32)
**And** la version de la toolchain est lue depuis `toolchain/version.txt` (NFR15)

### Story 4.2: Génération du code QMK et compilation du firmware

As a utilisateur (Pentinou ou Alex),
I want to click "Générer firmware" and watch my configuration compile into a .uf2 file,
So that I get a ready-to-flash firmware without writing any QMK code.

**Acceptance Criteria:**

**Given** j'ai configuré au minimum la sélection matériel (Epic 1)
**When** je clique "Générer firmware"
**Then** les templates Jinja2 sont rendus depuis `ProjectModel` → code source QMK généré dans un répertoire temporaire (FR16)

**Given** la génération du code source est terminée
**When** la compilation démarre
**Then** `arm-none-eabi-gcc` s'exécute dans un `BuildWorker(QThread)` — le thread UI reste réactif
**And** une barre de progression s'incrémente de 0 à 100% (FR20)
**And** les lignes de log de compilation apparaissent en temps réel dans une zone de texte défilante (FR20)

**Given** la compilation se termine avec succès
**When** le .uf2 est produit
**Then** sa taille est affichée (ex : "847 KB / 2048 KB utilisés") (FR17)
**And** le fichier est syntaxiquement valide (conforme au format UF2 Microsoft) (NFR6)
**And** la compilation s'est achevée en moins de 2 minutes sur une machine standard (NFR1)

**Given** la taille du firmware dépasse la capacité flash du MCU cible
**When** la vérification de taille s'effectue
**Then** un avertissement explicite est affiché avant tout export (FR18)
**And** l'utilisateur peut choisir de continuer ou d'annuler

### Story 4.3: Gestion des erreurs de compilation

As a utilisateur (Pentinou ou Alex),
I want to see readable error messages and a simplified diagnosis when a build fails,
So that I can understand what went wrong and fix it without reading raw QMK logs.

**Acceptance Criteria:**

**Given** la compilation échoue avec une erreur QMK connue
**When** l'erreur est capturée par le `BuildWorker`
**Then** un message lisible est affiché (ex : "La configuration RGB est invalide : couleur manquante pour l'effet ripple") (FR21)
**And** les logs QMK bruts restent accessibles dans la zone de log pour les utilisateurs avancés

**Given** la compilation échoue avec une erreur identifiable (ex : template invalide, toolchain absente)
**When** le diagnostic s'effectue
**Then** un message de diagnostic simplifié est proposé (ex : "La toolchain ARM est introuvable. Vérifiez que arm-none-eabi-gcc est installé.") (FR22)

**Given** la compilation échoue pour n'importe quelle raison
**When** l'erreur est affichée
**Then** l'application reste dans un état stable et utilisable (NFR8)
**And** je peux modifier ma configuration et relancer la compilation sans redémarrer l'application

**Given** un `BuildWorker` échoue avec une exception Python non gérée
**When** l'exception est catchée
**Then** le signal `error = Signal(str)` est émis avec un message d'erreur lisible
**And** aucune exception ne remonte jusqu'au thread UI Qt

### Story 4.4: Guide de flash, export du firmware et compatibilité Vial

As a utilisateur (Pentinou ou Alex),
I want to export my compiled .uf2 file and follow an illustrated flashing guide,
So that I can flash my keyboard and immediately use it with vial.rocks.

**Acceptance Criteria:**

**Given** la compilation s'est terminée avec succès
**When** je clique "Exporter le firmware"
**Then** une fenêtre de dialogue s'ouvre pour choisir l'emplacement de sauvegarde du .uf2 (FR28)
**And** le fichier .uf2 est copié à l'emplacement choisi

**Given** le firmware a été exporté
**When** je clique "Guide de flash"
**Then** un dialogue illustré s'ouvre avec les étapes (FR23, FR33) :
  1. Photo du bouton BOOT sur le PCB du Sofle
  2. Procédure : maintenir BOOT + brancher USB + relâcher
  3. Capture d'écran du lecteur "RPI-RP2" dans l'explorateur de fichiers
  4. Instruction de glisser-déposer du .uf2

**Given** je suis les étapes du guide de flash et que mon clavier est reconnecté
**When** je navigue sur vial.rocks
**Then** le clavier est reconnu immédiatement pour la configuration des layers et keymaps (FR24)
**And** cela valide que `vial.json.j2` a été correctement généré et inclus dans le firmware

**Given** l'application est lancée offline (sans internet)
**When** j'accède au guide de flash
**Then** le guide est affiché depuis les assets locaux — aucun appel réseau (FR29)
