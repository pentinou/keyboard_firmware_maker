"""download.py — téléchargement et extraction sûrs des archives de toolchain.

Utilisé par `msys2_manager` et `toolchain_installer`, qui récupèrent des
archives de ~100–250 Mo et les extraient dans le cache utilisateur.

Trois garanties, absentes de l'implémentation `urlretrieve` initiale :
1. **Timeout** — un miroir qui ne répond plus interrompt le téléchargement au
   lieu de bloquer l'application indéfiniment.
2. **Intégrité** — SHA-256 vérifié contre la valeur publiée par l'éditeur.
   Une archive corrompue ou substituée est supprimée, jamais extraite.
3. **Extraction confinée** — un membre d'archive dont le chemin sort du
   répertoire de destination (« Zip Slip ») fait échouer l'extraction.
"""
from __future__ import annotations

import hashlib
import logging
import tarfile
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import urlopen

logger = logging.getLogger(__name__)

# Délai maximal d'inactivité réseau. Volontairement court : il ne borne pas la
# durée totale du téléchargement, seulement l'attente d'un bloc de données.
NETWORK_TIMEOUT_S = 60

_CHUNK_SIZE = 256 * 1024


class ChecksumError(Exception):
    """L'archive téléchargée ne correspond pas au SHA-256 attendu."""


class UnsafeArchiveError(Exception):
    """L'archive contient un membre qui s'extrairait hors du dossier cible."""


def download_file(
    url: str,
    dest: Path,
    expected_sha256: str = "",
    progress_callback: Callable[[int], None] | None = None,
    timeout: int = NETWORK_TIMEOUT_S,
) -> Path:
    """Télécharge `url` vers `dest` en vérifiant son empreinte SHA-256.

    Args:
        url: adresse de l'archive.
        dest: fichier de destination (les parents sont créés).
        expected_sha256: empreinte attendue. Vide = vérification ignorée
            (un avertissement est journalisé).
        progress_callback: appelé avec un entier 0-100.
        timeout: délai d'inactivité réseau en secondes.

    Raises:
        ChecksumError: si l'empreinte ne correspond pas — le fichier est supprimé.
        OSError: si le réseau ou l'écriture échoue.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    downloaded = 0

    with urlopen(url, timeout=timeout) as response:  # noqa: S310 (URL constante, https)
        total = int(response.headers.get("Content-Length") or 0)
        with dest.open("wb") as out:
            while True:
                chunk = response.read(_CHUNK_SIZE)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    progress_callback(min(100, int(downloaded / total * 100)))

    actual = digest.hexdigest()
    if not expected_sha256:
        logger.warning("Aucun SHA-256 attendu pour %s — intégrité non vérifiée (obtenu %s)", url, actual)
        return dest

    if actual.lower() != expected_sha256.lower():
        dest.unlink(missing_ok=True)
        raise ChecksumError(
            f"Empreinte SHA-256 incorrecte pour {dest.name}.\n"
            f"Attendu : {expected_sha256}\nObtenu  : {actual}\n"
            "Le fichier a été supprimé. Réessayez ; si l'erreur persiste, "
            "le miroir de téléchargement est peut-être compromis."
        )
    logger.info("Archive vérifiée (SHA-256 conforme) : %s", dest.name)
    return dest


def _assert_within(dest: Path, target: Path, member_name: str) -> None:
    """Vérifie que `target` reste sous `dest` une fois les chemins résolus."""
    if not target.resolve().is_relative_to(dest.resolve()):
        raise UnsafeArchiveError(
            f"Archive refusée : le membre '{member_name}' s'extrairait hors de {dest}."
        )


def safe_extract_zip(archive: Path, dest: Path) -> None:
    """Extrait un .zip en refusant tout membre sortant de `dest`."""
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            _assert_within(dest, dest / name, name)
        zf.extractall(path=dest)


def safe_extract_tar(archive: Path, dest: Path) -> None:
    """Extrait un .tar[.gz|.xz] avec le filtre « data » de la stdlib.

    Le filtre neutralise les chemins absolus, les remontées `..`, les liens
    hors archive et les bits setuid. Sur les Python antérieurs à son
    introduction, on retombe sur une validation manuelle des chemins.
    """
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        try:
            tar.extractall(path=dest, filter="data")
        except TypeError:  # Python < 3.11.4 : pas de paramètre `filter`
            for member in tar.getmembers():
                _assert_within(dest, dest / member.name, member.name)
            tar.extractall(path=dest)  # noqa: S202 (chemins validés ci-dessus)
