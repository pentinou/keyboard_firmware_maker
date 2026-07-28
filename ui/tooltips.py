"""tooltips.py — infobulles explicatives des champs de l'interface.

Chaque champ porte un `objectName` ; la clé de traduction s'en déduit
(`tip.<objectName>`). Un onglet déclare la liste des champs à documenter et
appelle `apply_tooltips()` après avoir construit son UI.

Le texte d'une infobulle suit toujours la même structure :
    <ce que fait l'option>
    Exemple : <effet concret et observable>
    [avertissement éventuel]
    [option firmware sous-jacente]

Qt rend les infobulles en texte brut tant qu'elles ne contiennent pas de
balises ; les retours à la ligne des traductions sont donc conservés.
"""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QWidget

from i18n import tr

logger = logging.getLogger(__name__)

TOOLTIP_PREFIX = "tip."


def tooltip_for(object_name: str) -> str:
    """Retourne l'infobulle d'un champ, ou "" si aucune n'est définie."""
    key = f"{TOOLTIP_PREFIX}{object_name}"
    text = tr(key)
    # tr() renvoie la clé elle-même quand la traduction n'existe pas
    return "" if text == key else text


def apply_tooltips(root: QWidget, object_names: list[str]) -> int:
    """Pose l'infobulle de chaque champ nommé trouvé sous `root`.

    Les champs absents sont ignorés silencieusement : un onglet peut masquer
    ou ne pas construire certains widgets selon le clavier sélectionné.

    Returns:
        Nombre d'infobulles réellement posées.
    """
    applied = 0
    for name in object_names:
        text = tooltip_for(name)
        if not text:
            continue
        for widget in root.findChildren(QWidget, name):
            widget.setToolTip(text)
            applied += 1
    return applied
