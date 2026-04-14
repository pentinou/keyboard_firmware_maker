# Keyboard Firmware Maker — Guide utilisateur

Ce guide couvre tous les workflows de l'application, du premier lancement jusqu'au flash du firmware sur votre clavier.

---

## Table des matieres

1. [Premier lancement](#1-premier-lancement)
2. [Interface principale](#2-interface-principale)
3. [Onglet Hardware — Choix du clavier](#3-onglet-hardware--choix-du-clavier)
4. [Onglet OLED — Edition des ecrans](#4-onglet-oled--edition-des-ecrans)
5. [Onglet RGB — Effets lumineux](#5-onglet-rgb--effets-lumineux)
6. [Onglet Build — Compilation et flash](#6-onglet-build--compilation-et-flash)
7. [Gestion de projet](#7-gestion-de-projet)
8. [Creer un clavier custom (KLE Import)](#8-creer-un-clavier-custom-kle-import)
9. [Ajouter un clavier via YAML](#9-ajouter-un-clavier-via-yaml)
10. [Support ZMK (experimental)](#10-support-zmk-experimental)
11. [Raccourcis et astuces](#11-raccourcis-et-astuces)
12. [Depannage](#12-depannage)

---

## 1. Premier lancement

```bash
python main.py
```

Au premier lancement, l'application propose de cloner le depot **Vial-QMK**. Ce depot contient les sources QMK necessaires a la compilation et les fichiers `vial.json` de 620+ claviers.

**Ce qui se passe :**
1. Un dialogue apparait pour confirmer le clonage
2. Le depot est clone dans `~/.keyboard_firmware_maker/vial-qmk/`
3. Un index des claviers est construit et cache dans `~/.keyboard_firmware_maker/vial-qmk-index.json`
4. L'application est prete

> Le clonage n'a lieu qu'une seule fois. Les lancements suivants utilisent le cache.

---

## 2. Interface principale

L'application comporte **4 onglets** principaux :

| Onglet | Toujours actif ? | Description |
|--------|:-:|---|
| **Hardware** | Oui | Selection du clavier, MCU, layout |
| **OLED** | Si le clavier a un ecran | Edition des affichages OLED |
| **RGB** | Si le clavier a du RGB | Effets lumineux et couleurs par touche |
| **Build** | Oui | Compilation du firmware et flash |

Les onglets OLED et RGB s'activent/desactivent automatiquement selon les capacites du clavier selectionne. La checkbox "Activer RGB" dans l'onglet Hardware permet de forcer l'activation RGB meme si le clavier n'en a pas nativement.

**Menu Fichier :**
- **Nouveau** — Remet a zero le projet
- **Ouvrir** — Charge un fichier `.kfm.json`
- **Sauvegarder** / **Sauvegarder sous** — Enregistre la configuration complete

---

## 3. Onglet Hardware — Choix du clavier

### 3.1 Workflow principal : clavier compatible

1. **Filtrer par categorie** (optionnel) — Le menu deroulant propose : Tous, Split, Macropad, 40%, 60%, 75%, TKL, Fullsize
2. **Selectionner le clavier** dans la liste deroulante (survol = tooltip avec description)
3. **Choisir le MCU** (microcontroleur) — Les options disponibles dependent du clavier
4. **Choisir le variant de layout** (si le clavier en a, ex: PancakeXXL standard/7u)
5. **Configurer les options :**
   - Cotes OLED : Aucun / Gauche / Droite / Les deux
   - Checkbox RGB : activer/desactiver le support RGB

### 3.2 Les 4 claviers bundled

Ces claviers ont une definition YAML complete dans le dossier `keyboards/` :

| Clavier | Particularites |
|---------|----------------|
| **Sofle v2** | Split, RP2040, 2 encodeurs rotatifs, RGB, OLED |
| **Corne** | Split, 42 touches, 3 MCUs (Pro Micro, Elite-C, RP2040), OLED |
| **Lily58** | Split, 58 touches, 3 MCUs, OLED |
| **PancakeXXL** | Mono (non split), RP2040, 2 variants de layout (43 / 37 touches) |

### 3.3 Les 620+ claviers Vial-QMK

Les claviers indexes depuis le depot Vial-QMK utilisent le layout physique natif de leur fichier `vial.json`. Ils sont auto-categorises par nombre de touches et type.

### 3.4 Clavier custom (KLE)

Le bouton **"Custom / KLE"** bascule vers l'import de layout depuis keyboard-layout-editor.com. Voir [section 8](#8-creer-un-clavier-custom-kle-import).

---

## 4. Onglet OLED — Edition des ecrans

L'editeur OLED permet de designer l'affichage des ecrans 128x32 pixels (ou 128x64) de votre clavier split.

### 4.1 Canvas

- **Deux canvas** : un pour le cote gauche, un pour le cote droit
- Resolution : 32x128 pixels (orientation verticale), affiche en grille 6 colonnes x 16 lignes (unites curseur QMK)
- Fond noir = pixel eteint, blanc = pixel allume

### 4.2 Ajouter une image

1. Cliquer sur **"Ajouter image"** sous le canvas du cote souhaite
2. Selectionner un fichier PNG, BMP ou GIF
3. L'image apparait sur le canvas et peut etre deplacee par glisser-deposer
4. Le positionnement s'aligne sur la grille (6px colonnes, 8px lignes)

**Images animees (GIF) :**
- Les GIFs multi-frames sont detectes automatiquement
- Les frames sont extraites et jouees en boucle avec le delai d'origine
- Preview en temps reel dans le canvas

### 4.3 Overlays integres

Des widgets pre-configures peuvent etre actives et positionnes par glisser-deposer :

| Overlay | Description |
|---------|-------------|
| **Layer** | Affiche le numero de layer actif |
| **Caps Lock** | Indicateur d'etat Caps Lock |
| **WPM** | Vitesse de frappe en mots par minute |
| **RGB Mode** | Nom de l'effet RGB actif |
| **KFM** | Logo Keyboard Firmware Maker |

### 4.4 Animations integrees

| Animation | Taille | Description |
|-----------|--------|-------------|
| **Luna** | 32x22 px | Mascotte animee qui reagit a la vitesse de frappe |
| **Bongo Cat** | 32x128 px | Chat qui tape sur un clavier |
| **Ocean Dream** | 32x128 px | Scene de plage animee |
| **KatawaJojo** | 32x128 px | Animation japonaise |
| **Crab** | Variable | Crabe anime |

### 4.5 Options

- **Inversion** : inverser les pixels d'une image (noir ↔ blanc)
- **Anti burn-in** : timeout configurable pour eteindre l'ecran apres inactivite
- **Sleep mode** : eteint l'ecran apres un delai configurable

---

## 5. Onglet RGB — Effets lumineux

### 5.1 Vue d'ensemble

L'onglet RGB affiche une representation visuelle du clavier (layout physique) avec preview en temps reel des effets.

Deux modes de personnalisation :
- **Effets natifs** — 49 effets QMK pre-definis
- **Effets custom** — Timeline d'animation personnalisee

### 5.2 Couleurs par touche (per-key)

1. **Clic gauche** sur une touche du layout → ouvre le selecteur de couleur
2. La couleur est appliquee immediatement sur la touche
3. **Clic droit** sur une touche → menu contextuel (reset couleur, etc.)

Les couleurs per-key sont sauvegardees dans le projet et generees dans le firmware.

### 5.3 Effets natifs

La liste des effets est organisee en deux categories :

**Effets ambiants** (35 effets) — animation permanente, pas de declenchement :

| Sous-categorie | Effets |
|----------------|--------|
| Couleur unie | Solid Color, Alphas/Mods |
| Degrades | Gradient Haut/Bas, Gradient Gauche/Droite |
| Respiration | Breathing, Hue Breathing, Hue Pendulum, Hue Wave |
| Bandes | Band Saturation, Band Value, Band Pinwheel Sat/Val, Band Spiral Sat/Val |
| Cycles | Cycle All, Gauche→Droite, Haut→Bas, Exterieur→Centre, Pinwheel, Spiral |
| Arcs-en-ciel | Rainbow Chevron, Rainbow Beacon, Rainbow Pinwheels, Dual Beacon |
| Effets speciaux | Flower Blooming, Raindrops, Jellybean Raindrops, Riverflow |
| Pixels | Pixel Fractal, Pixel Flow, Pixel Rain |
| Etoiles | Starlight, Starlight (dual hue), Starlight (dual sat) |

**Effets reactifs** (14 effets) — declenches par appui sur une touche :

| Effet | Description |
|-------|-------------|
| Typing Heatmap | Les touches chauffent avec la frequence de frappe |
| Digital Rain | Effet "Matrix" avec des gouttes vertes |
| Solid Reactive (6 variantes) | Eclat colore a l'appui : Simple, Wide, Cross, Nexus, Splash et leurs variantes Multi |

### 5.4 Configurer un effet

1. **Selectionner** un effet dans la liste a gauche
2. **Couleur primaire** — Cliquer sur le bouton de couleur pour ouvrir le selecteur
3. **Couleur secondaire** — Disponible pour les effets a deux couleurs (degrades, reactive)
4. **Fade (ms)** — Vitesse de transition pour les effets reactive
5. **Touche trigger** — Pour les effets reactive : cliquer "Assigner trigger", puis cliquer la touche souhaitee sur le layout

Les checkboxes a cote de chaque effet permettent de choisir quels effets seront inclus dans le firmware (pour limiter la taille du binaire).

### 5.5 Preview en temps reel

- Les effets **ambiants** s'animent automatiquement sur le layout a 20 fps
- Les effets **reactive** simulent un appui de touche aleatoire avec propagation de l'onde
- La preview se met en pause quand l'onglet n'est pas visible (economie CPU)

### 5.6 Effets custom (timeline)

Pour creer un effet personalise :
1. Cliquer **"+ Nouvel effet"** sous la liste des effets
2. Choisir un nom et un type de base (static ou reactive)
3. Editer la timeline : ajouter des steps avec couleur, duree, et fondu
4. Preview en temps reel pendant l'edition

### 5.7 Underglow

Le champ **"LEDs underglow par cote"** permet de definir le nombre de LEDs sous le PCB (distinctes des LEDs per-key). La valeur -1 desactive l'underglow.

---

## 6. Onglet Build — Compilation et flash

### 6.1 Pre-requis

Avant la compilation, l'application verifie :
- La presence du depot Vial-QMK (`~/.keyboard_firmware_maker/vial-qmk/`)
- La toolchain `arm-none-eabi-gcc` (necessaire pour les MCU ARM)
- L'outil `make`

### 6.2 Workflow de compilation

1. **Configurer** votre clavier dans les onglets Hardware/OLED/RGB
2. Aller dans l'onglet **Build**
3. Cliquer **"Compiler"**
4. Le systeme :
   - Genere les fichiers source C via templates Jinja2
   - Lance `make` sur le depot Vial-QMK
   - Affiche la progression en temps reel (0-100%)
   - Affiche le log de compilation
5. Si la compilation reussit :
   - La taille du firmware est affichee
   - Le bouton **"Exporter .uf2"** devient actif
   - Un avertissement s'affiche si le firmware depasse la capacite flash du MCU

### 6.3 Exporter le firmware

Cliquer **"Exporter .uf2"** pour sauvegarder le fichier firmware a l'emplacement de votre choix.

### 6.4 Flash du firmware

Cliquer **"Guide de flash"** pour ouvrir un assistant illustre en 4 etapes :

1. **Preparer** — Debrancher le clavier
2. **Mode bootloader** — Appuyer deux fois sur le bouton reset (ou court-circuiter RST+GND)
3. **Copier** — Le clavier apparait comme un disque USB : copier le fichier `.uf2` dessus
4. **Verifier** — Le clavier redemarre automatiquement avec le nouveau firmware

> Pour les claviers split, repeter l'operation pour chaque moitie.

### 6.5 Erreurs de compilation

En cas d'erreur, le systeme analyse le log et propose un diagnostic :

| Erreur | Cause probable | Solution |
|--------|----------------|----------|
| Toolchain manquante | `arm-none-eabi-gcc` non installe | Installer via `apt install gcc-arm-none-eabi` |
| Erreur de syntaxe | Template corrompu | Verifier la configuration |
| Overflow flash | Firmware trop gros | Desactiver des effets RGB ou animations OLED |
| Erreur linker | Symbole manquant | Verifier le layout_macro dans le YAML |

---

## 7. Gestion de projet

### 7.1 Format de fichier

Les projets sont sauvegardes au format `.kfm.json` (JSON lisible). Un fichier contient :

```json
{
  "version": "1.0",
  "keyboard": {
    "model": "sofle-v2",
    "mcu": "rp2040",
    "oled_sides": ["left", "right"],
    "layout_variant": "",
    "rgb_enabled": true
  },
  "oled": { ... },
  "rgb": {
    "effects": [{"type": "breathing", "color_primary": "#FF0000", ...}],
    "per_key": {"L_r0_c0": "#FF0000", "R_r2_c3": "#0000FF"},
    "custom_effects": [...]
  },
  "build": { ... }
}
```

### 7.2 Sauvegarder

- **Ctrl+S** ou **Fichier > Sauvegarder**
- Premier enregistrement → dialogue "Sauvegarder sous"
- Les ecritures sont atomiques (fichier temporaire puis remplacement) pour eviter toute corruption

### 7.3 Ouvrir un projet

- **Ctrl+O** ou **Fichier > Ouvrir**
- L'application restaure : clavier, MCU, images OLED, couleurs RGB, effets, overlays
- Les anciennes versions de format sont migrees automatiquement

### 7.4 Nouveau projet

- **Fichier > Nouveau** — Remet tous les reglages par defaut

---

## 8. Creer un clavier custom (KLE Import)

Si votre clavier n'est pas dans la liste des 620+ claviers compatibles, vous pouvez creer sa definition depuis zero.

### 8.1 Etape 1 : Dessiner le layout sur KLE

1. Aller sur [keyboard-layout-editor.com](http://keyboard-layout-editor.com)
2. Dessiner votre layout (positions, tailles, rotations)
3. Copier le JSON brut (onglet "Raw data" du site)

### 8.2 Etape 2 : Importer dans l'application

1. Dans l'onglet Hardware, cliquer **"Custom / KLE"**
2. Coller le JSON dans la zone de texte
3. Cliquer **"Importer"** — le layout s'affiche dans le canvas

### 8.3 Etape 3 : Cablage de la matrice

Le canvas de cablage montre chaque touche. Pour chacune :
1. Assigner la **row** (ligne) de la matrice
2. Assigner la **column** (colonne) de la matrice
3. Pour les claviers split : indiquer le cote (gauche/droite)

### 8.4 Etape 4 : Configuration hardware

Renseigner :
- **Nom du clavier** (minuscules, tirets uniquement, ex: `my-keyboard-v2`)
- **MCU** : choisir parmi les presets (Pro Micro, RP2040, STM32F072, STM32F103, nRF52840) ou "Custom"
- **Bootloader** : rp2040, caterina, atmel-dfu, stm32-dfu, tinyuf2
- **Capacites** : OLED, RGB, encodeur

### 8.5 Etape 5 : Sauvegarder

Cliquer **"Sauvegarder"**. Le fichier YAML est enregistre dans :
```
~/.keyboard_firmware_maker/custom_keyboards/{nom}.yaml
```

Le clavier apparait immediatement dans la liste de l'onglet Hardware.

---

## 9. Ajouter un clavier via YAML

Pour les utilisateurs avances, il est possible de creer manuellement un fichier YAML.

### 9.1 Ou deposer le fichier

Deposer un fichier `.yaml` dans le dossier `keyboards/` du projet. Le nom du fichier (sans extension) doit correspondre au champ `model` a l'interieur.

### 9.2 Structure minimale

```yaml
model: ferris-sweep
display_name: "Ferris Sweep"
description: "34-key split keyboard."
mcu_options:
  - id: rp2040
    display_name: "RP2040"
    bootloader: "rp2040"
    pins:
      matrix_rows: ["GP29", "GP28", "GP27", "GP26"]
      matrix_cols: ["GP4", "GP5", "GP6", "GP7", "GP8"]
      serial_tx: "GP1"
      serial_driver: "vendor"
diode_direction: "COL2ROW"
layout_macro: "LAYOUT_split_3x5_2"
has_encoder: false
capabilities:
  oled: false
  rgb: false
matrix:
  rows: 4
  cols: 5
layout:
  left:
    - {row: 0, col: 0, x: 0.0, y: 0.0}
    # ... une entree par touche
  right:
    - {row: 0, col: 4, x: 0.0, y: 0.0}
    # ...
```

### 9.3 Champs optionnels avances

| Champ | Usage |
|-------|-------|
| `vial_qmk_keyboard` | Chemin vers le clavier dans vial-qmk (utilise le layout natif) |
| `oled.width/height/driver/rotation/display` | Configuration hardware OLED |
| `rgb.max_brightness` | Luminosite max RGB (0-255) |
| `layout_variants` | Variants de layout (ex: standard / 7u) |
| Pins encoder (`encoder_a/b`, `encoder_a_right/b_right`) | Si `has_encoder: true` |
| Pins RGB (`ws2812`, `ws2812_driver`) | Si `capabilities.rgb: true` |

> Documentation complete : [`keyboards/README.md`](../keyboards/README.md)

---

## 10. Support ZMK (experimental)

L'application peut generer une configuration **ZMK** (alternative a QMK) pour les MCU wireless nRF52840.

### Boards supportes

| Board | MCU |
|-------|-----|
| Nice!Nano v2 | nRF52840 |
| nRFMicro | nRF52840 |
| SuperMini nRF52840 | nRF52840 |

### Fichiers generes

La generation ZMK produit un dossier `config/boards/shields/{shield}/` contenant :
- `.overlay` — Devicetree shield configuration
- `.dtsi` — Matrix transform et bindings
- `.keymap` — Keymap avec layers
- `.conf` — Configuration Kconfig (RGB, OLED, etc.)

> Le support ZMK est experimental et ne couvre pas encore tous les workflows de build.

---

## 11. Raccourcis et astuces

### Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+S` | Sauvegarder le projet |
| `Ctrl+O` | Ouvrir un projet |
| `Ctrl+N` | Nouveau projet |

### Astuces

- **Preview RGB** : la preview s'arrete automatiquement quand vous quittez l'onglet RGB (economie CPU) et redemarre quand vous y revenez
- **Taille firmware** : desactivez les effets RGB inutilises (via les checkboxes) pour reduire la taille du binaire
- **Claviers non-split** : le PancakeXXL montre que l'app supporte aussi les claviers monofaces
- **Choix du MCU** : RP2040 offre le plus d'espace flash et RAM ; Pro Micro est le plus repandu mais limite en espace
- **Noms de pins** : utilisez la notation QMK — `GP0`–`GP29` pour RP2040, `B0`–`F7` pour AVR (Pro Micro / Elite-C)

---

## 12. Depannage

### Le clonage Vial-QMK echoue

- Verifier la connexion internet
- Verifier que `git` est installe : `git --version`
- Supprimer le dossier partiel et relancer : `rm -rf ~/.keyboard_firmware_maker/vial-qmk/`

### L'index des claviers est vide

- L'index est cache par SHA git. Si le depot a ete modifie manuellement, supprimer le cache :
  ```bash
  rm ~/.keyboard_firmware_maker/vial-qmk-index.json
  ```
- Relancer l'application

### La compilation echoue avec "toolchain not found"

```bash
# Ubuntu / Debian
sudo apt install gcc-arm-none-eabi

# Arch Linux
sudo pacman -S arm-none-eabi-gcc
```

### Le firmware est trop gros (flash overflow)

- Desactiver les effets RGB non utilises (checkboxes dans la liste)
- Reduire le nombre d'animations OLED
- Utiliser un MCU avec plus de flash (RP2040 = 2 MB)

### L'application ne demarre pas sous WSL2

- Installer un serveur X : `sudo apt install x11-apps`
- Verifier que `$DISPLAY` est configure
- Avec WSLg (Windows 11) : devrait fonctionner directement

### Les images OLED ne s'affichent pas correctement

- Les images doivent etre en 1-bit (noir et blanc) pour un rendu optimal
- Le format supporte : PNG, BMP, GIF
- Dimensions recommandees : largeur max 32px, hauteur max 128px (orientation verticale)
