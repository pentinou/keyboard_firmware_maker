---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
classification:
  projectType: desktop_app
  domain: general_iot_embedded
  complexity: medium
  projectContext: greenfield
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-keyboard_firmware_maker-2026-02-21.md'
workflowType: 'prd'
briefCount: 1
researchCount: 0
brainstormingCount: 0
projectDocsCount: 0
---

# Product Requirements Document — keyboard_firmware_maker

**Author:** Pentinou
**Date:** 2026-02-22

---

## Vision & Contexte

keyboard_firmware_maker est une application desktop open source permettant
aux passionnés de claviers mécaniques split de créer, personnaliser et
flasher leur propre firmware QMK/Vial-QMK sans expertise en développement
embarqué. Elle cible en premier lieu le Sofle 2.1 RGB (RP2040, filaire)
et produit directement un fichier .uf2 prêt à flasher.

**Problème résolu :** Les firmwares communautaires sont toujours incomplets
(colonnes cassées, effets RGB absents, OLED incorrect), tandis que compiler
soi-même un firmware QMK requiert des compétences en C et une chaîne de
compilation complexe. keyboard_firmware_maker supprime cette barrière
technique.

**Solution :** Un workflow « import-first » — l'utilisateur importe ses
assets (GIF, images), configure visuellement ses effets RGB, et l'application
génère automatiquement un firmware Vial-QMK compilé, prêt à flasher, sans
toucher une seule ligne de code.

**Différenciateurs clés :**
- Première application desktop unifiée combinant éditeur OLED visuel,
  éditeur RGB, compatibilité Vial-QMK et génération .uf2 autonome pour
  claviers mécaniques split RP2040
- Toolchain de compilation embarquée — zéro installation externe requise
- 100% offline, aucun telemetry, aucune collecte de données
- Open source et gratuit — binaires + code source distribués librement sur GitHub

**Portée MVP :** Sofle 2.1 RGB — RP2040 — filaire — Windows + Linux.
Projet personnel non-monétisé, sans contrainte de calendrier.

---

## Product Scope

### MVP — Phase 1 (Sofle 2.1 RGB, filaire, Windows + Linux)

1. **Sélection matériel**
   - Choix du modèle (Sofle 2.1 RGB, Corne, Lily58)
   - Choix du microcontrôleur filaire (RP2040, Pro Micro, Elite-C)
   - Détection automatique des capacités (OLED, RGB) et masquage dynamique
     des sections non applicables

2. **Éditeur OLED**
   - Import GIF / PNG / BMP avec conversion automatique 1-bit 64×128px
   - Prévisualisation pixel-perfect dans l'application
   - Affichage d'infos système (layer actif, Caps Lock, WPM)

3. **Éditeur RGB visuel**
   - Sélection de touches, choix de couleur par touche
   - Effets de base : couleur statique, ripple au keystroke (rouge → orange → fade)
   - Déclencheurs sur touches spécifiques

4. **Génération firmware**
   - Compilation Vial-QMK embarquée
   - Vérification taille firmware vs capacité MCU avant flash
   - Sortie : fichier .uf2
   - Guide de flash illustré (procédure mode bootloader)
   - Messages d'erreur lisibles (diagnostic si faisable, logs QMK sinon)

5. **Distribution**
   - Binaire autonome Windows (.exe) + Linux (AppImage)
   - Code source open source sur GitHub

### Post-MVP — Phase 2 (Enrichissement)

- Import de code C existant pour effets RGB et animations OLED
  (Bongo Cat, Luna, effets communautaires)
- Éditeur OLED frame-by-frame
- Effets RGB avancés (vague espace, animations complexes)
- Support macOS
- Architecture de définition claviers (YAML) documentée pour contributeurs

### Vision — Phase 3+ (Expansion)

- Support claviers Bluetooth / ZMK
- Autres modèles de claviers (Kyria, Iris, Dactyl...)
- Bibliothèque d'effets RGB et animations OLED partageables
- Interface de contribution communautaire pour nouveaux modèles

---

## User Journeys

### Parcours 1 — Pentinou : Configuration complète depuis zéro (succès)

**Personnage :** Pentinou, sysadmin, Sofle 2.1 RGB déjà assemblé. Il a essayé
de compiler un firmware QMK il y a six mois — colonnes de touches cassées,
abandon. Son clavier tourne avec un firmware communautaire "presque bon"
qui agace depuis des mois.

**Scène d'ouverture :** Un soir, Pentinou télécharge keyboard_firmware_maker.
Double-clic sur l'AppImage — l'app s'ouvre directement, sans installer quoi
que ce soit. Il sélectionne "Sofle 2.1 RGB" dans la liste des claviers,
choisit "RP2040" comme microcontrôleur. L'interface affiche la représentation
visuelle de son clavier split en deux moitiés.

**Action montante :** Il clique sur "OLED". L'app lui propose d'importer une
image. Il glisse son logo personnel (PNG 200x200px). L'app le convertit
automatiquement en bitmap 1-bit 64×128px et affiche la prévisualisation
pixel-perfect à l'écran — exactement ce qu'il verra sur son clavier.
Satisfait, il active aussi "WPM" et "Layer actif" en overlay.

Il passe à l'onglet "RGB". Il choisit l'effet "Ripple au keystroke" :
configure rouge pour la touche pressée, orange pour les voisines, fade
progressif. Il voit un aperçu animé de l'effet dans l'interface.

**Climax :** Il clique sur "Générer firmware". Une barre de progression
apparaît — "Compilation en cours...". 90 secondes plus tard : "✓ Firmware
généré — 847 KB / 2048 KB utilisés". L'app lui affiche les instructions :
"Maintenez le bouton BOOT de la moitié gauche, branchez en USB, relâchez.
Un lecteur 'RPI-RP2' apparaît. Glissez-déposez le fichier .uf2."

**Résolution :** Pentinou suit les instructions. Le Sofle se reconnecte.
Son logo s'affiche sur l'OLED. Il tape "Hello" — le ripple rouge/orange
s'exécute parfaitement. Il ouvre vial.rocks, son clavier est reconnu
immédiatement. Il configure son layer gaming en 5 minutes.
Après des mois de compromis, son clavier lui appartient enfin.

**Capabilities révélées :** Sélection matériel, import image OLED,
prévisualisation 1-bit, éditeur RGB visuel, compilation embarquée,
vérification taille firmware, guide de flash, compatibilité Vial.

---

### Parcours 2 — Alex : Premier flash (débutant complet)

**Personnage :** Alex, 24 ans, vient de finir de souder son kit Sofle en
suivant un tutoriel YouTube. Aucune connaissance en développement.
Il a passé 3 heures sur Reddit à admirer les setups Bongo Cat des autres.

**Scène d'ouverture :** Alex cherche "sofle firmware bongo cat" sur Reddit.
Quelqu'un lui répond avec un lien vers keyboard_firmware_maker. Il télécharge
le .exe sous Windows. L'app s'ouvre — interface claire, liste de claviers.
Il reconnaît "Sofle 2.1 RGB" et clique dessus.

**Action montante :** L'app lui pose deux questions : modèle ✓, micro-
contrôleur. Il ne sait pas ce qu'est un "RP2040". Une info-bulle explique :
"Le Sofle 2.1 utilise deux RP2040 — sélectionnez RP2040". Il comprend,
il clique. L'app masque automatiquement les options non applicables.

Il va dans "OLED", clique "Importer GIF", sélectionne un Bongo Cat GIF
trouvé sur GitHub. L'app le convertit et affiche l'animation frame par
frame en prévisualisation 64×128px. Alex sourit — c'est exactement ça.

Il active l'effet RGB "Ripple" depuis les présets visuels. Il ne touche
à rien d'autre et clique sur "Générer firmware".

**Climax :** "✓ Firmware généré". L'app affiche un guide illustré étape
par étape : photo du bouton BOOT sur le PCB, flèche vers le port USB,
capture d'écran du lecteur RPI-RP2 sous Windows Explorer. Alex suit
chaque étape sans hésiter.

**Résolution :** Le Sofle se reconnecte. Bongo Cat anime les pattes sur
l'OLED gauche. Alex tape frénétiquement pour voir le ripple RGB. Il prend
une photo, la poste sur Reddit : "Mon premier firmware custom, 15 minutes,
zéro code." 47 upvotes.

**Capabilities révélées :** Info-bulles contextuelles sur le matériel,
masquage dynamique des options, import GIF avec aperçu animé, présets RGB,
guide de flash illustré.

---

### Parcours 3 — Pentinou : Récupération après firmware défectueux

**Personnage :** Pentinou, même profil. Il a généré un firmware, mais après
le flash, la colonne de touches la plus à droite de la moitié gauche ne
répond pas. Frustrant — exactement le problème qu'il avait avant.

**Scène d'ouverture :** Pentinou rouvre keyboard_firmware_maker. L'app
retrouve son projet précédent (config sauvegardée). Il navigue vers la
configuration du layout de touches.

**Action montante :** Il inspecte le mapping de la colonne problématique.
Il réalise qu'une ligne du matrix est mal configurée — il corrige les
assignations de touches pour cette colonne. L'app lui propose de regénérer.

**Climax :** Nouveau cycle de compilation. "✓ Firmware généré — 849 KB".
Pentinou reflashe son Sofle (il connaît maintenant la procédure par cœur).

**Résolution :** Toutes les touches répondent. La correction était simple
une fois qu'il pouvait visualiser le problème dans l'interface. Il note
mentalement que c'est infiniment plus rapide que de déboguer du code C.

**Capabilities révélées :** Sauvegarde/rechargement de projet, modification
incrémentale de la configuration, cycle de regénération rapide.

---

### Parcours 4 — Contributeur : Ajout du support Kyria

**Personnage :** Marie, développeuse avec expérience QMK, possède un Kyria.
Elle découvre keyboard_firmware_maker sur GitHub, l'app ne supporte pas
encore son clavier. Elle veut contribuer.

**Scène d'ouverture :** Marie clone le dépôt. Elle lit la documentation
"Ajouter un nouveau clavier". L'architecture est claire : un fichier de
définition YAML par modèle, qui décrit les capacités (OLED, RGB, matrix,
microcontrôleur).

**Action montante :** Elle crée `kyria.yaml` en suivant le template fourni.
Elle renseigne les specs (pas d'OLED, RGB oui, RP2040, matrix 5×12).
Elle lance l'app en mode développement — le Kyria apparaît dans la liste.
Elle teste le workflow complet : sélection → RGB → génération → .uf2 valide.

**Climax :** Elle ouvre une Pull Request sur GitHub. La CI valide
automatiquement la structure du fichier de définition.

**Résolution :** Sa PR est mergée. Le Kyria est disponible dans la version
suivante. Marie documente son expérience dans le README contributeur.

**Capabilities révélées :** Architecture de définition de claviers en YAML,
documentation contributeur, CI de validation des définitions.

---

### Journey Requirements Summary

| Capability | Révélée par |
|---|---|
| Sélection clavier + microcontrôleur avec aide contextuelle | Parcours 1, 2 |
| Import image/GIF → conversion 1-bit + prévisualisation | Parcours 1, 2 |
| Éditeur RGB visuel (présets + personnalisation) | Parcours 1, 2 |
| Compilation embarquée + vérification taille mémoire | Parcours 1, 2, 3 |
| Guide de flash illustré (texte + visuels) | Parcours 1, 2 |
| Compatibilité Vial-QMK post-flash | Parcours 1 |
| Sauvegarde/rechargement de projet | Parcours 3 |
| Cycle regénération incrémental | Parcours 3 |
| Architecture de définition claviers (YAML/extensible) | Parcours 4 |
| Documentation contributeur + CI de validation | Parcours 4 |

---

## Success Criteria

### User Success

- L'utilisateur complète le workflow complet (sélection clavier → configuration
  OLED/RGB → génération → instructions de flash) en moins de 20 minutes,
  sans expérience préalable en QMK
- Le firmware généré fonctionne du premier flash : 100% des touches répondent,
  l'OLED affiche le contenu configuré, les effets RGB s'exécutent comme définis
- Le firmware est reconnu et pleinement configurable via vial.rocks (layers,
  keymaps) immédiatement après le flash
- Aucune installation manuelle de dépendances requise ; si des pré-requis
  existent, ils sont clairement documentés dans l'application elle-même
- La prévisualisation OLED dans l'application est pixel-perfect et reflète
  exactement le rendu sur les écrans 64×128px (1 bit, noir et blanc strict,
  aucun niveau de gris)

### Technical Success

- Le firmware compilé respecte les limites de la mémoire flash du
  microcontrôleur cible ; si la taille dépasse la capacité (ex : 2MB pour
  le RP2040), l'application avertit l'utilisateur avant toute tentative de flash
- La compilation QMK/Vial-QMK embarquée s'exécute en moins de 2 minutes
  sur une machine standard
- L'application ne plante pas durant le workflow de génération
- Les fichiers .uf2 produits sont valides et flashables par glisser-déposer
  en mode bootloader
- La conversion GIF/image → bitmap 1-bit pour l'OLED est correcte et fidèle
  (dithering adapté si nécessaire pour les images en niveaux de gris)

### Measurable Outcomes

| Critère | Cible | Priorité |
|---|---|---|
| Temps workflow complet (débutant) | < 20 minutes | Must Have |
| Touches fonctionnelles après flash | 100% | Must Have |
| Prévisualisation OLED pixel-perfect | 1-bit, 64×128px exact | Must Have |
| Compatibilité Vial post-flash | Reconnaissance immédiate | Must Have |
| Temps de compilation | < 2 minutes | Should Have |
| Vérification taille firmware | Avertissement si dépassement | Must Have |
| Diagnostic erreur firmware | Diagnostic si faisable, logs sinon | Should Have |
| Zéro dépendance externe | App autonome ou instructions intégrées | Must Have |

---

## Functional Requirements

### 1. Gestion du Matériel

- FR1: L'utilisateur peut sélectionner son modèle de clavier parmi une
  liste intégrée (Sofle 2.1 RGB, Corne, Lily58)
- FR2: L'utilisateur peut sélectionner le microcontrôleur de son clavier
  (RP2040, Pro Micro, Elite-C)
- FR3: Le système détecte automatiquement les capacités du clavier
  sélectionné (présence OLED, présence RGB)
- FR4: Le système masque dynamiquement les sections non applicables au
  clavier sélectionné (ex : onglet RGB masqué si pas de LEDs)
- FR5: L'utilisateur peut consulter une aide contextuelle décrivant chaque
  modèle de clavier et microcontrôleur

### 2. Personnalisation OLED

- FR6: L'utilisateur peut importer un fichier GIF, PNG ou BMP comme
  contenu à afficher sur l'écran OLED
- FR7: Le système convertit automatiquement l'image ou GIF importé en
  bitmap 1-bit 64×128 pixels
- FR8: L'utilisateur peut prévisualiser le rendu OLED pixel-perfect dans
  l'application avant génération du firmware
- FR9: Le système affiche les frames d'un GIF importé en prévisualisation
  animée dans l'application
- FR10: L'utilisateur peut configurer l'affichage d'informations système
  sur l'OLED (layer actif, état Caps Lock, WPM)

### 3. Programmation RGB

- FR11: L'utilisateur peut assigner une couleur spécifique à une ou
  plusieurs touches individuelles via une interface visuelle
- FR12: L'utilisateur peut sélectionner un effet RGB prédéfini parmi
  une liste (couleur statique uniforme, ripple au keystroke)
- FR13: L'utilisateur peut configurer les paramètres d'un effet ripple
  (couleur de la touche pressée, couleur des touches voisines, vitesse
  de fondu)
- FR14: L'utilisateur peut assigner des effets RGB déclenchés par des
  touches spécifiques
- FR15: L'utilisateur peut prévisualiser un aperçu animé des effets RGB
  configurés dans l'application

### 4. Génération du Firmware

- FR16: Le système compile la configuration utilisateur en firmware
  Vial-QMK compatible
- FR17: Le système vérifie que la taille du firmware compilé respecte
  la capacité flash du microcontrôleur cible
- FR18: Le système avertit l'utilisateur si la taille du firmware dépasse
  la capacité mémoire du MCU sélectionné
- FR19: Le système produit un fichier .uf2 valide prêt à être flashé
- FR20: Le système affiche la progression de la compilation en temps réel
- FR21: Le système affiche les erreurs de compilation de manière lisible
  (messages humanisés, pas de logs QMK bruts)
- FR22: Le système propose un diagnostic d'erreur simplifié lorsque la
  cause de l'échec est identifiable
- FR23: Le système fournit un guide de flash illustré intégré (procédure
  mode bootloader, étapes de glisser-déposer du .uf2)
- FR24: Le firmware généré est compatible avec vial.rocks pour la
  configuration des layers et keymaps

### 5. Gestion de Projet

- FR25: L'utilisateur peut sauvegarder sa configuration en cours dans
  un fichier projet local
- FR26: L'utilisateur peut recharger un projet précédemment sauvegardé
- FR27: L'utilisateur peut modifier une configuration existante et
  regénérer le firmware sans repartir de zéro
- FR28: L'utilisateur peut exporter le fichier .uf2 généré vers
  l'emplacement de son choix sur son système de fichiers

### 6. Application & Distribution

- FR29: L'application fonctionne sans connexion réseau (mode offline
  complet — aucune fonctionnalité ne nécessite Internet)
- FR30: L'application fonctionne sans droits administrateur
- FR31: L'application affiche sa version courante dans une section
  "À propos"
- FR32: L'application s'exécute sans installation de dépendances
  externes, ou fournit des instructions d'installation claires
  directement dans l'interface
- FR33: L'utilisateur peut accéder aux guides d'utilisation et à la
  documentation de flash depuis l'application

---

## Non-Functional Requirements

### Performance

- NFR1: La compilation du firmware s'exécute en moins de 2 minutes sur
  une machine avec des spécifications standard (processeur x64 moderne,
  4 Go de RAM minimum)
- NFR2: Les interactions UI (sélection de touche, changement de couleur,
  navigation entre onglets) répondent en moins de 200ms
- NFR3: La prévisualisation OLED se met à jour en moins de 500ms après
  import ou modification d'un asset
- NFR4: Le démarrage de l'application s'effectue en moins de 5 secondes
  sur une machine standard

### Reliability

- NFR5: L'application ne plante pas durant un workflow de génération
  complet (de la sélection du clavier à l'export du .uf2)
- NFR6: Tout fichier .uf2 produit par l'application est syntaxiquement
  valide (conforme au format UF2 Microsoft)
- NFR7: La sauvegarde d'un projet ne corrompra pas un fichier projet
  existant (écriture atomique ou vérification d'intégrité)
- NFR8: Un échec de compilation ne laisse pas l'application dans un état
  bloqué — l'utilisateur peut corriger et relancer sans redémarrer l'app

### Compatibility

- NFR9: L'application fonctionne sur Windows 10 et Windows 11 (x64)
- NFR10: L'application fonctionne sur les distributions Linux majeures
  avec glibc ≥ 2.31 (Ubuntu 20.04+, Debian 11+, Fedora 33+)
- NFR11: L'AppImage Linux fonctionne sans installation de paquets
  supplémentaires sur les distributions cibles
- NFR12: Le firmware généré est compatible avec les versions stables
  de Vial-QMK supportant le RP2040

### Maintainability

- NFR13: Les définitions de claviers sont stockées dans des fichiers
  de configuration séparés (YAML ou JSON) — l'ajout d'un nouveau modèle
  ne nécessite pas de modifier le code source de l'application
- NFR14: Le code source est documenté suffisamment pour qu'un développeur
  tiers puisse comprendre l'architecture et contribuer sans assistance
- NFR15: La toolchain QMK embarquée est versionnée explicitement —
  une mise à jour de Vial-QMK ne casse pas silencieusement les firmwares
  générés

---

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Première application desktop unifiée pour firmware de claviers split**
Aucun outil existant ne combine en une seule application : éditeur OLED visuel,
éditeur d'effets RGB, compatibilité Vial-QMK et génération .uf2 autonome pour
des claviers mécaniques split avec RP2040. Les solutions existantes (QMK
Configurator, Via, Vial) adressent chacune une partie du problème — jamais
l'ensemble.

**2. Workflow "import-first" : du visuel au firmware embarqué**
L'approche distinctive de keyboard_firmware_maker est d'inverser le paradigme :
plutôt que de demander à l'utilisateur d'écrire du code C pour personnaliser
son firmware, il importe des assets visuels (GIF, images) et configure des
effets via une interface graphique. La traduction vers le code QMK est
entièrement transparente.

**3. Abstraction de la chaîne de compilation embarquée**
Embarquer et orchestrer la toolchain QMK/Vial-QMK (compilation croisée ARM,
gestion des dépendances, génération .uf2) de manière transparente pour un
utilisateur non-technique est une approche non triviale qui n'a pas encore
été réalisée dans un outil grand public pour ce segment.

### Market Context & Competitive Landscape

- **QMK Configurator** : configurateur en ligne, pas d'OLED, pas de RGB
  programmable, pas de .uf2 RP2040
- **Via / Vial** : excellents pour le remapping de touches en temps réel,
  mais aucune personnalisation OLED ni animation RGB
- **Firmwares communautaires GitHub** : incomplets, difficiles à adapter,
  requièrent des connaissances en C
- **keyboard_firmware_maker** : premier outil à couvrir l'ensemble du
  workflow de personnalisation pour les claviers split avancés

### Validation Approach

- **Validation primaire** : Pentinou génère et flashe un firmware 100%
  fonctionnel sur son Sofle 2.1 RGB sans intervention manuelle dans QMK
- **Validation secondaire** : un utilisateur sans expérience QMK complète
  le workflow de A à Z en moins de 20 minutes
- **Validation technique** : le .uf2 généré est valide, flashable, et
  reconnu par vial.rocks

### Risk Mitigation

| Risque | Probabilité | Mitigation |
|---|---|---|
| Toolchain QMK trop lourde à embarquer | Moyenne | Dockerisation ou instructions d'installation claires intégrées à l'app |
| Incompatibilités entre versions Vial-QMK | Moyenne | Versionner la toolchain embarquée, tests de non-régression |
| Conversion GIF → 1-bit dégradée | Faible | Algorithmes de dithering éprouvés (Floyd-Steinberg), prévisualisation fidèle |
| Taille firmware dépasse flash MCU | Faible | Vérification automatique avant flash avec avertissement explicite |

---

## Desktop Application Specific Requirements

### Project-Type Overview

keyboard_firmware_maker est une application desktop native, entièrement
autonome et hors-ligne. Elle ne requiert aucune connexion réseau pour
fonctionner. L'utilisateur gère lui-même les mises à jour (via GitHub)
et le flash du clavier (glisser-déposer du .uf2).

### Platform Support

| Plateforme | Version | Statut |
|---|---|---|
| Windows | 10 / 11 (x64) | MVP — must have |
| Linux | Ubuntu 20.04+ / distributions majeures (x64) | MVP — must have |
| macOS | 12+ (Intel + Apple Silicon) | v2 — post-MVP |

**Format de distribution :**
- Windows : exécutable `.exe` autonome (portable ou installable)
- Linux : `AppImage` (aucune installation requise, double-clic)
- Toutes dépendances embarquées ou clairement documentées dans l'app

### System Integration

- **Accès fichiers :** Lecture/écriture pour import d'assets (GIF, PNG, BMP),
  sauvegarde de projets, export du fichier .uf2
- **Pas de détection USB automatique** : l'utilisateur passe son clavier
  en mode bootloader et effectue le glisser-déposer du .uf2 manuellement
- **Pas d'élévation de privilèges requise** : l'app fonctionne sans droits
  administrateur
- **Aucune connexion réseau** : fonctionnement 100% offline, aucun telemetry,
  aucune collecte de données

### Update Strategy

- **Pas de mise à jour automatique** — l'utilisateur vérifie et gère les
  mises à jour manuellement via les releases GitHub
- L'application affiche sa version courante dans l'interface (menu "À propos")
  pour faciliter la comparaison avec les releases disponibles

### Offline Capabilities

- **Entièrement offline** : toutes les fonctionnalités sont disponibles
  sans connexion réseau
- La toolchain QMK/Vial-QMK est embarquée dans l'application (ou
  installée localement avec instructions intégrées)
- Les définitions de claviers (Sofle, Corne, Lily58) sont embarquées
  localement — aucun téléchargement requis à l'utilisation
- Les projets utilisateur sont sauvegardés localement (format fichier
  ouvert, JSON ou YAML)

### Implementation Considerations

- **Framework UI :** À définir en phase architecture (candidats : Python +
  PySide6/PyQt6, Tauri/Rust, Electron) — doit supporter le packaging
  cross-platform autonome
- **Toolchain embarquée :** La compilation QMK requiert une chaîne croisée
  ARM (arm-none-eabi-gcc) — envisager Docker, Podman, ou binaires pré-compilés
  statiques selon la faisabilité de packaging
- **Format de projet :** Les configurations utilisateur doivent être
  sauvegardables et rechargeable (fichier projet portable)
- **Logs de compilation :** Afficher les logs QMK de manière lisible en cas
  d'erreur, avec diagnostic simplifié si faisable

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**Approche MVP :** Problem-solving MVP — livrer la solution minimale qui
résout le problème core de Pentinou : générer un firmware Sofle 2.1 RGB
100% fonctionnel sans toucher à du code QMK.

**Ressources :** Projet solo (développeur unique). Pas de contrainte de
calendrier. L'architecture doit être simple à maintenir par une seule
personne.

**Philosophie :** Faire fonctionner d'abord, optimiser ensuite. Chaque
fonctionnalité ajoutée au MVP doit être justifiée par un besoin concret
des parcours utilisateurs définis.

### MVP Feature Set — Parcours Supportés

- Parcours 1 : Pentinou — configuration complète depuis zéro
- Parcours 2 : Alex — premier flash débutant
- Parcours 3 : Pentinou — récupération après firmware défectueux

*(Parcours 4 — Contributeur : post-MVP, nécessite architecture stabilisée)*

**Capacités indispensables (Must-Have) :**

| Capacité | Justification |
|---|---|
| Sélection clavier (Sofle, Corne, Lily58) + MCU filaire | Sans ça, l'app ne démarre pas |
| Détection capacités (OLED/RGB) + masquage dynamique | Évite la confusion pour les claviers sans RGB/OLED |
| Import GIF/PNG/BMP → conversion 1-bit 64×128px | Besoin core Pentinou + Alex |
| Prévisualisation OLED pixel-perfect | Critère de succès non-négociable |
| Éditeur RGB visuel simple (couleur par touche, ripple) | Différenciateur principal |
| Compilation Vial-QMK embarquée → .uf2 | Sans ça, le produit n'existe pas |
| Vérification taille firmware vs capacité MCU | Sécurité, évite firmware inutilisable |
| Guide de flash illustré intégré | Critère < 20 min pour débutant |
| Sauvegarde/rechargement de projet | Parcours 3 — récupération essentielle |
| Messages d'erreur lisibles (logs QMK humanisés) | Réduction friction débutant |
| Distribution Windows .exe + Linux AppImage | Cible utilisateurs MVP |

### Risk Mitigation Strategy

**Risques techniques :**

| Risque | Sévérité | Mitigation |
|---|---|---|
| Embarquer la toolchain QMK/ARM est trop complexe | Élevée | Docker/Podman en fallback ; instructions d'installation intégrées à l'app comme alternative acceptable |
| Incompatibilités futures Vial-QMK | Moyenne | Versionner la toolchain embarquée ; ne pas dépendre de la dernière version |
| Conversion GIF 1-bit de mauvaise qualité | Faible | Algorithme Floyd-Steinberg ; prévisualisation fidèle pour validation avant génération |
| Framework UI inadapté au packaging cross-platform | Moyenne | Prototyper le packaging avant de s'engager sur un framework |

**Risques projet (solo) :**

| Risque | Mitigation |
|---|---|
| Scope creep (fonctionnalités non-MVP) | Backlog explicite, MVP figé, post-MVP documenté |
| Complexité technique sous-estimée | MVP limité au Sofle — aucune généralisation prématurée |
| Maintenance à long terme | Architecture modulaire, code documenté, définitions claviers en YAML |
