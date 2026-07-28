"""Tests pour modules/build_manager/download.py.

Les installeurs MSYS2 / toolchain ARM récupéraient ~100–250 Mo par
`urlretrieve` sans timeout, sans vérification d'intégrité, puis appelaient
`extractall()` sans contrôle des chemins.
"""
from __future__ import annotations

import hashlib
import io
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.build_manager.download import (
    ChecksumError,
    UnsafeArchiveError,
    download_file,
    safe_extract_tar,
    safe_extract_zip,
)

PAYLOAD = b"toolchain-archive-content" * 100
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


class _FakeResponse(io.BytesIO):
    """Réponse HTTP minimale : lecture par blocs + Content-Length."""

    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


@pytest.fixture
def fake_urlopen():
    with patch("modules.build_manager.download.urlopen") as mock:
        mock.return_value = _FakeResponse(PAYLOAD)
        yield mock


class TestDownloadFile:
    def test_writes_file_and_accepts_matching_checksum(self, tmp_path, fake_urlopen):
        dest = tmp_path / "archive.zip"

        download_file("https://example.invalid/a.zip", dest, expected_sha256=PAYLOAD_SHA)

        assert dest.read_bytes() == PAYLOAD

    def test_rejects_and_deletes_on_checksum_mismatch(self, tmp_path, fake_urlopen):
        dest = tmp_path / "archive.zip"

        with pytest.raises(ChecksumError):
            download_file("https://example.invalid/a.zip", dest, expected_sha256="00" * 32)

        assert not dest.exists(), "l'archive corrompue doit être supprimée"

    def test_empty_checksum_keeps_file_but_warns(self, tmp_path, fake_urlopen, caplog):
        dest = tmp_path / "archive.zip"

        download_file("https://example.invalid/a.zip", dest, expected_sha256="")

        assert dest.exists()
        assert any("intégrité non vérifiée" in r.getMessage() for r in caplog.records)

    def test_passes_timeout_to_urlopen(self, tmp_path, fake_urlopen):
        download_file("https://example.invalid/a.zip", tmp_path / "a.zip", PAYLOAD_SHA, timeout=42)

        assert fake_urlopen.call_args.kwargs["timeout"] == 42

    def test_reports_progress(self, tmp_path, fake_urlopen):
        seen: list[int] = []

        download_file("https://example.invalid/a.zip", tmp_path / "a.zip", PAYLOAD_SHA, seen.append)

        assert seen and seen[-1] == 100
        assert all(0 <= p <= 100 for p in seen)

    def test_creates_parent_directories(self, tmp_path, fake_urlopen):
        dest = tmp_path / "nested" / "dir" / "a.zip"

        download_file("https://example.invalid/a.zip", dest, PAYLOAD_SHA)

        assert dest.is_file()


def _zip_with(tmp_path: Path, members: dict[str, str]) -> Path:
    archive = tmp_path / "test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return archive


def _tar_with(tmp_path: Path, members: dict[str, str]) -> Path:
    archive = tmp_path / "test.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name, content in members.items():
            data = content.encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return archive


class TestSafeExtractZip:
    def test_extracts_normal_archive(self, tmp_path):
        archive = _zip_with(tmp_path, {"bin/gcc.exe": "elf", "readme.txt": "hello"})
        dest = tmp_path / "out"

        safe_extract_zip(archive, dest)

        assert (dest / "bin" / "gcc.exe").read_text() == "elf"
        assert (dest / "readme.txt").read_text() == "hello"

    def test_rejects_path_traversal(self, tmp_path):
        archive = _zip_with(tmp_path, {"../evil.txt": "pwned"})
        dest = tmp_path / "out"

        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(archive, dest)

        assert not (tmp_path / "evil.txt").exists()

    def test_rejects_deep_path_traversal(self, tmp_path):
        archive = _zip_with(tmp_path, {"ok.txt": "fine", "a/b/../../../evil.txt": "pwned"})

        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(archive, tmp_path / "out")


class TestSafeExtractTar:
    def test_extracts_normal_archive(self, tmp_path):
        archive = _tar_with(tmp_path, {"usr/bin/make": "elf"})
        dest = tmp_path / "out"

        safe_extract_tar(archive, dest)

        assert (dest / "usr" / "bin" / "make").read_text() == "elf"

    def test_rejects_path_traversal(self, tmp_path):
        archive = _tar_with(tmp_path, {"../evil.txt": "pwned"})
        dest = tmp_path / "out"

        # `filter="data"` lève une erreur de la stdlib ; le fallback lève UnsafeArchiveError
        with pytest.raises((UnsafeArchiveError, tarfile.TarError)):
            safe_extract_tar(archive, dest)

        assert not (tmp_path / "evil.txt").exists()

    def test_absolute_path_stays_inside_destination(self, tmp_path):
        """Un membre `/etc/passwd` est réancré sous `dest`, jamais écrit à la racine."""
        archive = _tar_with(tmp_path, {"/etc/passwd": "pwned"})
        dest = tmp_path / "out"

        safe_extract_tar(archive, dest)

        assert (dest / "etc" / "passwd").read_text() == "pwned"

    def test_rejects_symlink_pointing_outside(self, tmp_path):
        """Vecteur réel : un lien qui sort de l'archive une fois déréférencé."""
        archive = tmp_path / "link.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            link = tarfile.TarInfo(name="evil-link")
            link.type = tarfile.SYMTYPE
            link.linkname = "../../../etc/passwd"
            tar.addfile(link)

        with pytest.raises((UnsafeArchiveError, tarfile.TarError)):
            safe_extract_tar(archive, tmp_path / "out")
