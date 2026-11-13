# Keyboard Firmware Maker en interface web, derrière YunoHost (branche `yunohost`)

Cette branche ajoute à l'application de bureau :

- **`web/` + `kfm_web.py`** : une interface web (même charte qu'IA Launcher) avec les cinq onglets
  de l'application — Matériel, OLED, RGB (dont l'éditeur d'effets personnalisés avec aperçu animé),
  Options avancées (import de keymap compris), Build. Elle réutilise tel quel le code Python
  (modèle de projet, générateurs QMK/ZMK, workers de compilation) : seules les fenêtres Qt sont
  remplacées. Les projets sont les mêmes `.kfm.json` que ceux de l'application de bureau.
- **`ynh/`** : le paquet YunoHost de la tuile (même principe que celui d'IA Launcher : la tuile
  renvoie vers la machine qui compile, derrière le SSO, avec une page « PC éteint » et un bouton
  « Réveiller le PC »).
- **`linux/installer-service-web.sh`** : démarrage automatique de l'interface (systemd).

## Pourquoi la compilation reste sur le PC

Compiler demande vial-qmk (~1 Go), arm-none-eabi-gcc, le Zephyr SDK et le workspace ZMK
(~2 Go), tous déjà installés dans WSL. Le serveur YunoHost (Core 2 sans SSE4.2) ne fait donc
que la tuile : il ne lance aucune compilation.

## Lancer à la main

    ./start.sh                         # une fois : crée .venv avec les dépendances
    .venv/bin/python kfm_web.py        # ouvre http://127.0.0.1:8767

## Mon installation

- **Machine qui compile** : le PC Windows (192.168.1.20), KFM dans WSL (`Ubuntu-24.04`, réseau
  `mirrored`, systemd actif). Démarrage automatique, depuis ce dossier :

      sudo sh linux/installer-service-web.sh --allow 192.168.1.179,192.168.1.20

  (192.168.1.179 : le portail YunoHost ; 192.168.1.20 : le PC lui-même, pour l'ouvrir par son
  adresse réseau.) Le pare-feu Hyper-V de WSL doit laisser entrer le port 8767 : vérifier que la
  règle `WSL-projets-YunoHost` le couvre, sinon l'ajouter.
- **Portail** : YunoHost `gingerfox.run`, tuile par exemple `kfm.gingerfox.run`, installée depuis
  ce dossier `ynh/` :

      sudo yunohost app install ./ynh -a "domain=kfm.gingerfox.run&path=/&upstream=http://192.168.1.20:8767&label=Keyboard Firmware Maker&mac=00:D8:61:76:42:BF&init_main_permission=admins"

  **Après installation ou mise à jour, revérifier les permissions de la tuile**
  (`yunohost user permission list kfm`) : seule `admins` doit y figurer.

## Sécurité

L'interface n'a pas d'authentification : c'est le SSO YunoHost qui protège l'accès, et
`--allow` n'accepte que le portail. Ne l'ouvrez qu'à des personnes de confiance : un projet
peut contenir du code C (effets RGB « code manuel ») compilé sur le PC, et les erreurs de
compilation s'affichent dans le journal.

Le serveur ne garde pas les projets (ils vivent dans le navigateur) ; il stocke seulement les
images OLED envoyées et les dix derniers firmwares compilés, dans
`~/.keyboard_firmware_maker/web/`.
