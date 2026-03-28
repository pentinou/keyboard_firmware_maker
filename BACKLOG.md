# Backlog — keyboard_firmware_maker

Idées et évolutions futures notées en cours de développement.

---

## ~~Support Windows natif~~ (v0.2.0 — en cours)

**Statut : implémenté**, en attente de tests sur machine Windows.

**Ce qui a été fait :**
- [x] Versioning centralisé (`_version.py`)
- [x] `builder.py` : résolution make via `msys2_manager.resolve_make_command()`
- [x] `msys2_manager.py` : téléchargement/installation MSYS2 automatique au premier build
- [x] `toolchain_installer.py` : téléchargement ARM gcc automatique
- [x] `toolchain.py` : détection dans vendored → downloaded → system PATH
- [x] `widget.py` : flux build Windows avec dialogues d'installation
- [x] `keyboard_firmware_maker.spec` : PyInstaller one-directory
- [x] `scripts/build_windows.bat` : script de build automatisé
- [x] `start.bat` : vérifications git/make/gcc, suppression message WSL2
- [x] i18n : clés MSYS2 + toolchain en FR/EN/IT
- [x] README : installation Windows documentée

**Reste à faire :**
- [ ] Tester sur Windows 10/11 natif
- [ ] Installeur Inno Setup (`installer/kfm_setup.iss`)
- [ ] Icône `.ico` (conversion de `bunny_crossbones.png`)
- [ ] CI/CD GitHub Actions Windows
- [ ] Signer le binaire (certificat code-signing)

---
