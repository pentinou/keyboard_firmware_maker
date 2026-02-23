# Story 4.3: Gestion des erreurs de compilation

Status: done

## Story

As a utilisateur (Pentinou ou Alex),
I want to see readable error messages and a simplified diagnosis when a build fails,
So that I can understand what went wrong and fix it without reading raw QMK logs.

## Acceptance Criteria

1. **Given** la compilation échoue avec une erreur QMK connue
   **When** l'erreur est capturée par le BuildWorker
   **Then** un message lisible est affiché (ex : "La configuration RGB est invalide") (FR21)
   **And** les logs QMK bruts restent accessibles dans la zone de log

2. **Given** la compilation échoue avec une erreur identifiable
   **When** le diagnostic s'effectue
   **Then** un message de diagnostic simplifié est proposé (FR22)
   ex : "La toolchain ARM est introuvable. Vérifiez que arm-none-eabi-gcc est installé."

3. **Given** la compilation échoue pour n'importe quelle raison
   **When** l'erreur est affichée
   **Then** l'application reste stable et utilisable (NFR8)
   **And** je peux modifier ma configuration et relancer sans redémarrer

4. **Given** un BuildWorker échoue avec une exception Python non gérée
   **When** l'exception est catchée
   **Then** le signal `error = Signal(str)` est émis avec un message lisible
   **And** aucune exception ne remonte jusqu'au thread UI Qt

## Tasks / Subtasks

- [x] Task 1: Créer modules/build_manager/error_classifier.py (AC: 1, 2)
  - [x] 1.1 `ErrorDiagnosis` dataclass : `message`, `diagnosis`, `pattern_matched`
  - [x] 1.2 `_ERROR_PATTERNS` : liste de (regex, message_lisible, diagnostic)
  - [x] 1.3 `classify_build_error(log_lines: list[str]) -> ErrorDiagnosis`
  - [x] 1.4 Patterns couverts : toolchain absente, erreur syntaxe C, référence indéfinie,
           template invalide, mémoire insuffisante, cible make introuvable

- [x] Task 2: Intégrer error_classifier dans builder.py (AC: 1, 2, 4)
  - [x] 2.1 Accumuler les log lines dans `self._log_lines: list[str]` pendant le build
  - [x] 2.2 Appeler `classify_build_error(self._log_lines)` quand returncode != 0
  - [x] 2.3 Émettre `error.emit(diagnosis.message)` avec le message humanisé
  - [x] 2.4 Vérifier que `try/except Exception` dans `run()` couvre tous les cas (AC: 4)

- [x] Task 3: Mettre à jour widget.py pour afficher le diagnostic (AC: 1, 2, 3)
  - [x] 3.1 `_on_build_error(msg)` : afficher diagnostic dans QMessageBox si présent
  - [x] 3.2 Réactiver le bouton build après erreur (déjà OK en 4.2)
  - [x] 3.3 Ajouter label `lbl_build_status` pour l'état courant

- [x] Task 4: Tests (AC: 1, 2, 4)
  - [x] 4.1 Créer `modules/build_manager/tests/test_error_classifier.py`
  - [x] 4.2 Tester classify_build_error avec log toolchain absente
  - [x] 4.3 Tester classify_build_error avec erreur C connue
  - [x] 4.4 Tester classify_build_error avec log inconnu → message générique
  - [x] 4.5 Tester que BuildWorker.run() ne lève pas d'exception si generator plante
  - [x] 4.6 Vérifier `python3 -m pytest tests/ modules/ -v` — aucune régression

## Dev Notes

### ErrorDiagnosis

```python
@dataclass
class ErrorDiagnosis:
    message: str     # message lisible court (FR21)
    diagnosis: str   # diagnostic actionnable (FR22)
    pattern_matched: str | None  # nom du pattern, None si générique
```

### _ERROR_PATTERNS

```python
# 7 patterns dans l'implémentation réelle (notes initiales en avaient 6 — permission_error ajouté)
_ERROR_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    # (pattern, pattern_name, message, diagnosis)
    (re.compile(r"arm-none-eabi-gcc.*(not found|no such file)|command not found.*gcc", re.IGNORECASE),
     "toolchain_missing",
     "La toolchain ARM est introuvable.",
     "Vérifiez que arm-none-eabi-gcc est installé sur votre système."),

    (re.compile(r"error:.*unknown type name|error:.*undeclared identifier", re.IGNORECASE),
     "syntax_error",
     "Erreur de syntaxe dans le code QMK généré.",
     "Vérifiez la configuration RGB ou OLED — un paramètre invalide a été détecté."),

    (re.compile(r"undefined reference to", re.IGNORECASE),
     "linker_error",
     "Erreur de liaison (linker) : fonction non définie.",
     "Une fonction QMK requise est manquante. Vérifiez que les bons modules sont activés dans rules.mk."),

    (re.compile(r"region .* overflowed|firmware too large|will not fit in program space", re.IGNORECASE),
     "flash_overflow",
     "Le firmware est trop volumineux pour le microcontrôleur.",
     "Désactivez certaines fonctionnalités (OLED, RGB, WPM) pour réduire la taille du firmware."),

    (re.compile(r"No rule to make target|no targets specified", re.IGNORECASE),
     "make_target_missing",
     "Cible de compilation introuvable.",
     "Le répertoire Vial-QMK est peut-être corrompu. Supprimez ~/.keyboard_firmware_maker/vial-qmk et relancez l'application."),

    (re.compile(r"TemplateNotFound|jinja2.*error|TemplateSyntaxError", re.IGNORECASE),
     "template_error",
     "Erreur dans les templates de génération du code.",
     "Les templates Jinja2 sont manquants ou corrompus. Réinstallez l'application."),

    (re.compile(r"cannot open output file|permission denied", re.IGNORECASE),
     "permission_error",
     "Impossible d'écrire les fichiers de compilation.",
     "Vérifiez les droits d'accès au répertoire de cache (~/.keyboard_firmware_maker/)."),
]

_GENERIC_MESSAGE = "La compilation a échoué."
_GENERIC_DIAGNOSIS = "Consultez les logs ci-dessus pour le détail de l'erreur."
```

### classify_build_error

```python
def classify_build_error(log_lines: list[str]) -> ErrorDiagnosis:
    full_log = "\n".join(log_lines)
    for pattern, name, message, diagnosis in _ERROR_PATTERNS:
        if pattern.search(full_log):
            return ErrorDiagnosis(message=message, diagnosis=diagnosis, pattern_matched=name)
    return ErrorDiagnosis(
        message=_GENERIC_MESSAGE,
        diagnosis=_GENERIC_DIAGNOSIS,
        pattern_matched=None,
    )
```

### References

- FR21 : messages d'erreur lisibles (sans jargon technique QMK)
- FR22 : diagnostic simplifié avec action corrective
- NFR8 : app reste stable et utilisable après erreur

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Story 4.3 implémentée avec succès — 246/246 tests passés, zéro régression (2026-02-23)
- `error_classifier.py` : 7 patterns regex couvrent les cas courants (toolchain, linker, flash, template...)
- Piège regex : "arm-none-eabi-gcc: No such file or directory" ne contient pas "not found" → pattern étendu avec `|no such file`
- `builder.py` : `self._log_lines` accumulé pendant le build, classifier appelé sur returncode != 0 ET sur exception non gérée
- `widget.py` : `lbl_build_status` mis à jour à chaque étape ("en cours..." / "réussie." / "Échec...")
- Les logs QMK bruts restent visibles dans `build_log` (AC: 1)

### File List

- `modules/build_manager/error_classifier.py` (nouveau — ErrorDiagnosis, classify_build_error, 7 patterns)
- `modules/build_manager/builder.py` (modifié — _log_lines accumulé, classifier intégré)
- `modules/build_manager/widget.py` (modifié — lbl_build_status, status updates)
- `modules/build_manager/tests/test_error_classifier.py` (nouveau — 19 tests)
