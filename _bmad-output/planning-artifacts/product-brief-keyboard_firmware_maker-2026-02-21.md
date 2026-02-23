---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
date: 2026-02-21
author: Pentinou
---

# Product Brief: keyboard_firmware_maker

## Executive Summary

keyboard_firmware_maker est une application desktop open source permettant
aux passionnés de claviers mécaniques split de créer, personnaliser et
flasher leur propre firmware QMK/Vial-QMK sans expertise en développement.
L'application cible en premier lieu le Sofle 2.1 RGB (RP2040) et produit
directement un fichier .uf2 prêt à flasher. Elle offre un éditeur visuel
pour les écrans OLED (import GIF/image, conversion automatique), un éditeur
d'effets RGB (interface graphique + import de code), et une compatibilité
complète Vial-QMK pour la gestion des layers et keymaps via vial.rocks.
L'application est entièrement packagée, autonome, gratuite et open source.

---

## Core Vision

### Problem Statement

Les utilisateurs de claviers mécaniques split avancés (Sofle, Lily58, Corne)
disposant d'écrans OLED et de LEDs RGB sont confrontés à une impasse : les
firmwares communautaires existants sont toujours incomplets (colonnes de
touches cassées, effets RGB absents, OLED affichant des informations erronées
ou des graphismes buggés), tandis que compiler soi-même un firmware QMK
personnalisé requiert des compétences en C et une chaîne de compilation
complexe, source d'erreurs difficiles à diagnostiquer.

### Problem Impact

L'utilisateur se retrouve contraint de choisir entre un firmware "presque bon"
qui ne satisfait jamais tous ses besoins, ou de plonger dans un écosystème
technique (QMK, toolchain ARM/RP2040, C embarqué) long à maîtriser. Les
fonctionnalités les plus désirées — animations OLED personnalisées (logo,
Bongo Cat, Luna), effets RGB complexes (vague sur espace, ripple au keystroke)
— restent inaccessibles au commun des passionnés.

### Why Existing Solutions Fall Short

- **QMK Configurator** : pas de gestion OLED, pas d'effets RGB programmables,
  pas de support natif RP2040 split
- **Via / Vial** : excellents pour les remaps de touches, mais aucune
  personnalisation des graphismes OLED ni des animations RGB
- **Firmwares communautaires** : toujours partiels — il manque systématiquement
  le bon layout, les bons effets, ou les bonnes infos OLED
- **Compilation manuelle QMK** : barrière technique élevée, erreurs de
  compilation opaques, processus long et fragile

### Proposed Solution

Une application desktop multiplateforme (Windows/Linux/Mac), entièrement
autonome et packagée, qui permet de :

1. **Composer son firmware** : layout de touches, layers, compatibilité Vial-QMK
2. **Personnaliser les écrans OLED** : import de GIF/images avec conversion
   automatique pour les écrans 64×128px du Sofle, affichage d'infos système
3. **Programmer les effets RGB** : via interface visuelle (timeline,
   déclencheurs sur touches) ou import de code C existant (Luna, Bongo Cat...)
4. **Générer le firmware** : compilation embarquée → fichier .uf2 prêt à
   flasher sur les deux processeurs RP2040 du Sofle 2.1 RGB

Cible initiale : Sofle 2.1 RGB. Extension prévue : Lily58, Corne.

### Key Differentiators

- **Première application desktop** combinant éditeur OLED + effets RGB +
  Vial-QMK pour claviers split RP2040
- **Workflow import-first** : GIF → firmware, code communautaire → firmware,
  sans friction technique
- **Entièrement packagée** : aucune dépendance externe à installer, ou
  instructions d'installation intégrées à l'app
- **100% open source et gratuit** : code source + binaires distribués
  librement, communauté first

---

## Target Users

### Primary Users

#### Persona 1 — Pentinou, l'Administrateur Système Bricoleur

**Profil :** Homme, 30-45 ans, administrateur système Linux. Bonnes bases
techniques générales (scripting, réseau, C/Python/Rust), mais débutant complet
en développement firmware embarqué et en écosystème QMK. Possède un Sofle 2.1
RGB déjà assemblé.

**Motivations :** Contrôle total sur son outil de travail quotidien. Ne supporte
pas d'utiliser un firmware "presque bon" — il veut son logo, ses effets RGB
précis, ses infos OLED exactes. Curieux techniquement mais ne veut pas perdre
des semaines à maîtriser QMK.

**Problème vécu :** A tenté de compiler un firmware custom. Résultat : colonnes
de touches cassées, OLED qui affiche des mauvaises infos, effets RGB absents.
Les firmwares communautaires ne conviennent jamais sur tous les points.

**Workarounds actuels :** Utilise des firmwares tiers partiellement satisfaisants,
compromis permanents entre ce qu'il veut et ce qui fonctionne.

**Moment de succès :** Flashe son Sofle avec son logo perso sur l'OLED, l'effet
vague sur la barre d'espace qui fonctionne exactement comme imaginé, toutes les
touches répondent. Premier essai, aucune ligne de code à écrire.

---

#### Persona 2 — Alex, le Passionné Reddit en Kit

**Profil :** Homme ou femme, 20-35 ans, découvert le monde des claviers
mécaniques via r/MechanicalKeyboards. Vient de recevoir son kit Sofle, l'a
soudé lui-même en suivant un guide YouTube. Aucune connaissance en
développement, zéro expérience QMK.

**Motivations :** Veut un clavier qui lui ressemble — animations OLED sympas
(Bongo Cat, Luna, son propre logo), LEDs qui font "wow". A passé des heures
sur Reddit à admirer les setups des autres et veut le même résultat.

**Problème vécu :** Le firmware de base est fade. Il a trouvé un firmware
custom sur GitHub mais la moitié des touches ne marchent pas et l'OLED reste
noir. Il ne sait pas compiler, ne comprend pas les erreurs QMK, abandonne.

**Workarounds actuels :** Utilise le firmware stock ou un firmware Reddit
trouvé par hasard — jamais vraiment satisfait, mais bloqué faute de solution.

**Moment de succès :** Télécharge l'app, sélectionne "Sofle 2.1 RGB", importe
un GIF de Bongo Cat, active l'effet ripple RGB, clique sur "Générer firmware",
flashe son clavier. 15 minutes, zéro ligne de code, résultat parfait.

---

### Secondary Users

#### Persona 3 — Le Contributeur Open Source

**Profil :** Développeur avec expérience QMK ou embarqué, qui découvre le
projet sur GitHub. Veut étendre le support à son propre clavier (Lily58, Corne,
Kyria...).

**Rôle :** Contributeur secondaire — pas l'utilisateur cible du MVP, mais
important pour la pérennité et l'adoption communautaire du projet.

**Besoin clé :** Architecture claire et documentée pour ajouter facilement
la définition d'un nouveau modèle de clavier.

---

### User Journey

#### Journey d'Alex (Persona 2 — cas le plus représentatif)

**1. Découverte**
Poste sur r/MechanicalKeyboards : "Mon Sofle est assemblé mais le firmware
par défaut est nul, comment faire ?". Quelqu'un lui répond avec un lien vers
keyboard_firmware_maker.

**2. Onboarding**
Télécharge le binaire (Windows .exe ou Linux AppImage). Lance l'app —
elle se lance directement, pas d'installation de dépendances. Sélectionne
son modèle : "Sofle 2.1 RGB". L'app lui montre une représentation visuelle
de son clavier.

**3. Personnalisation**
- Importe un GIF Bongo Cat → l'app le convertit et prévisualise le rendu
  sur les 64×128px de l'OLED
- Active l'effet RGB "ripple sur keypress" via l'interface visuelle
- Vérifie que ses layers Vial sont corrects

**4. Génération & Flash**
Clique sur "Générer firmware". L'app compile en arrière-plan et produit
un fichier .uf2. L'app lui indique comment passer le clavier en mode
bootloader et glisser-déposer le fichier.

**5. Moment Aha**
Le clavier se reconnecte. Bongo Cat s'anime sur l'OLED. Il tape une lettre —
la LED devient rouge, les voisines orange, la vague s'estompe. Il ouvre
vial.rocks pour vérifier ses layers. Tout fonctionne.

**6. Long terme**
Revient dans l'app pour modifier un effet. Partage son expérience sur Reddit
avec un lien vers le projet. Devient ambassadeur organique du projet.

---

## Success Metrics

### Définition du Succès

keyboard_firmware_maker est avant tout un projet personnel open source.
Le succès se mesure à la satisfaction fonctionnelle et à la qualité
technique — pas à l'adoption ou à la croissance.

**Critère ultime :** Pentinou peut générer et flasher un firmware parfaitement
fonctionnel pour son Sofle 2.1 RGB — toutes touches actives, OLED personnalisé,
effets RGB exacts — sans toucher une seule ligne de QMK manuellement.

---

### User Success Metrics

| Critère | Indicateur de succès |
|---|---|
| Firmware fonctionnel | 100% des touches répondent après flash |
| OLED personnalisé | Logo/GIF importé s'affiche correctement sur 64×128px |
| Effets RGB | Les effets définis (ripple, vague espace) fonctionnent comme spécifié |
| Compatibilité Vial | Le firmware flashé est reconnu et configurable via vial.rocks |
| Autonomie débutant | Un utilisateur sans expérience QMK flashe son premier firmware en < 20 min |
| Zéro friction | Aucune installation manuelle de dépendances requise pour l'utilisateur final |

---

### Business Objectives

N/A — projet open source non-monétisé. Les objectifs sont purement
techniques et personnels.

**Objectifs projet :**
- Livrer une version fonctionnelle pour le Sofle 2.1 RGB (MVP)
- Maintenir une architecture extensible pour Lily58/Corne (v2+)
- Distribuer binaires + code source librement

---

### Key Performance Indicators

**Qualité technique (non-négociables) :**
- Le firmware généré démarre sans erreur sur les deux RP2040 du Sofle
- L'application ne plante pas durant le workflow de génération
- La taille du firmware compilé reste dans les limites mémoire du RP2040
- Les fichiers .uf2 générés sont valides et flashables par glisser-déposer

**Expérience utilisateur :**
- Workflow complet (config → génération → flash) en < 20 minutes
  pour un débutant complet
- Messages d'erreur compréhensibles et actionnables (pas de logs QMK bruts)
- Prévisualisation OLED fidèle au rendu réel sur le clavier

**Extensibilité (horizon v2) :**
- Architecture permettant d'ajouter un nouveau modèle de clavier
  sans réécrire le coeur de l'application

---

## MVP Scope

### Core Features (v1 — claviers filaires uniquement)

#### 1. Sélection du clavier et du matériel
- Choix du modèle de clavier parmi une liste intégrée :
  Sofle 2.1 RGB, Corne, Lily58 (specs issues des dépôts GitHub officiels)
- Choix du microcontrôleur filaire : RP2040, Pro Micro, Elite-C
- Détection automatique des capacités du clavier sélectionné :
  présence ou non d'OLED, présence ou non de LEDs RGB
- Masquage dynamique des sections non applicables
  (ex : pas d'OLED → section OLED masquée)

#### 2. Personnalisation OLED
- Import de fichiers GIF ou image (PNG, BMP...)
- Conversion automatique vers le format compatible 64×128px OLED
- Prévisualisation du rendu sur l'écran simulé dans l'application
- Affichage d'informations système de base (layer actif, Caps Lock, WPM)

#### 3. Éditeur RGB visuel (simple)
- Interface visuelle de base : sélection de touches, choix de couleur
- Définition d'effets simples : couleur statique par touche,
  ripple au keystroke (rouge → orange → fade)
- Déclencheurs sur touches spécifiques
- Effets complexes (vague espace, etc.) progressivement ajoutés
  via l'éditeur au fil des versions

#### 4. Génération du firmware
- Compilation Vial-QMK embarquée (aucune installation externe requise,
  ou instructions claires intégrées à l'app si impossible)
- Sortie : fichier .uf2 prêt à flasher par glisser-déposer
- Guide de flash intégré (comment passer en mode bootloader)
- Messages d'erreur lisibles (pas de logs QMK bruts)

#### 5. Application desktop
- Plateforme : Windows + Linux
- Distribution : binaire autonome packagé (.exe / AppImage)
- Open source : code source + binaires disponibles librement

---

### Out of Scope for MVP

| Fonctionnalité | Raison du report |
|---|---|
| Support macOS | Priorité Windows + Linux d'abord |
| Claviers Bluetooth (ZMK) | Écosystème firmware différent, complexité doublée |
| Import de code C RGB (Luna, Bongo Cat...) | v2 — éditeur visuel d'abord |
| Éditeur OLED frame-by-frame | v2 — import GIF suffit pour le MVP |
| Effets RGB complexes préprogrammés | Intégrés progressivement via l'éditeur |
| Support d'autres claviers (Kyria, Iris...) | Architecture extensible, ajout en v2+ |

---

### MVP Success Criteria

- Le Sofle 2.1 RGB de Pentinou fonctionne à 100% avec un firmware
  généré par l'application (toutes touches actives, OLED, RGB, Vial)
- Un débutant complet réalise son premier flash en moins de 20 minutes
- Aucune dépendance externe à installer manuellement
- Le .uf2 généré est valide et flashable du premier coup

---

### Future Vision

**v2 — Enrichissement :**
- Import de code C existant pour les effets RGB et animations OLED
  (Bongo Cat, Luna, effets communautaires)
- Éditeur OLED frame-by-frame
- Effets RGB avancés (vague espace, animations complexes)
- Support macOS

**v3+ — Expansion :**
- Support claviers Bluetooth / ZMK
- Support d'autres modèles de claviers (Kyria, Iris, Dactyl...)
- Interface de contribution pour ajouter des modèles communautaires
- Bibliothèque d'effets RGB et animations OLED partageables
