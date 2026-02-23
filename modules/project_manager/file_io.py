# modules/project_manager/file_io.py
from __future__ import annotations

import json
import logging
from pathlib import Path

from models.project_model import ProjectModel

logger = logging.getLogger(__name__)


def save_project(model: ProjectModel, path: Path) -> None:
    """Sauvegarde le ProjectModel en JSON avec écriture atomique (NFR7).

    Pattern : écriture dans .tmp → replace() atomique.
    Lève OSError si l'écriture échoue — ne jamais avaler l'exception.
    """
    data = model.to_dict()
    content = json.dumps(data, indent=2, ensure_ascii=False)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    logger.info("Projet sauvegardé : %s", path)


def load_project(path: Path) -> ProjectModel:
    """Charge un ProjectModel depuis un fichier JSON.

    Lève OSError si le fichier est inaccessible.
    Lève json.JSONDecodeError si le JSON est malformé.
    """
    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    model = ProjectModel.from_dict(data)
    logger.info("Projet chargé : %s", path)
    return model
