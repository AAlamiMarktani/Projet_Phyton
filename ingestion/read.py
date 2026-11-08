"""
in  : un dossier (ex: ./data/auth) contenant des logs bruts (.log, .1, .2, .gz, .zip, .tar, .tar.gz ...)
out : liste de lignes (str)
"""

import gzip
import hashlib
import os
import tarfile
import zipfile
import zlib

from config import get_logger

logger = get_logger("ingestion")

GZIP_MAGIC = b"\x1f\x8b"


def _is_gzip(file_path: str) -> bool:
    # On teste le contenu et pas l'extension : "auth.log" peut etre un .tar.gz
    with open(file_path, "rb") as f:
        return f.read(2) == GZIP_MAGIC


def _open_text(file_path: str):
    if _is_gzip(file_path):
        return gzip.open(file_path, mode="rt", encoding="utf-8", errors="replace")
    return open(file_path, mode="r", encoding="utf-8", errors="replace")


def _decode(data: bytes) -> list[str]:
    # un fichier dans une archive peut lui-meme etre un .gz
    if data[:2] == GZIP_MAGIC:
        data = gzip.decompress(data)
    return data.decode("utf-8", errors="replace").splitlines()


def _archive_files(file_path: str):
    """Genere (nom, lignes) pour chaque fichier d'une archive (.tar, .tar.gz ou .zip)."""
    if tarfile.is_tarfile(file_path):
        with tarfile.open(file_path) as t:
            for member in t.getmembers():
                if member.isfile():
                    yield member.name, _decode(t.extractfile(member).read())
    else:
        with zipfile.ZipFile(file_path) as z:
            for name in z.namelist():
                if not name.endswith("/"):
                    yield name, _decode(z.read(name))


def _files(path: str):
    """Genere (nom, lignes) pour chaque fichier du dossier, et pour chaque fichier des archives."""
    for name in sorted(os.listdir(path)):
        file_path = os.path.join(path, name)
        if not os.path.isfile(file_path):
            continue
        try:
            # archive (tar, tar.gz, zip) : on lit les fichiers qu'elle contient
            if tarfile.is_tarfile(file_path) or zipfile.is_zipfile(file_path):
                yield from _archive_files(file_path)
            else:
                with _open_text(file_path) as f:
                    yield name, f.read().splitlines()
        except (
            OSError,
            EOFError,
            zlib.error,
            tarfile.TarError,
            zipfile.BadZipFile,
        ) as e:
            logger.error(f"{name} : lecture impossible ({e})")


def iter_lines(path: str):
    """Genere toutes les lignes de tous les fichiers du dossier (un meme contenu n'est lu qu'une fois)."""
    vus = set()
    for name, lines in _files(path):
        # une archive peut contenir les memes logs que ceux du dossier : on ne les compte pas 2 fois
        empreinte = hashlib.sha256(
            "\n".join(lines).encode("utf-8", errors="replace")
        ).hexdigest()
        if empreinte in vus:
            logger.warning(f"{name} a deja ete lu, ignore (doublon)")
            continue
        vus.add(empreinte)
        logger.info(f"{name} : {len(lines)} lignes lues")
        yield from lines


def ingest(path: str) -> list[str]:
    """Retourne la liste de toutes les lignes (sans le \\n final)."""
    try:
        return list(iter_lines(path))
    except FileNotFoundError:
        logger.error(f"Dossier introuvable : {path}")
        return []
    except OSError as e:
        logger.error(f"Dossier illisible : {path} ({e})")
        return []


if __name__ == "__main__":
    data = ingest("./data/auth")
    if data:
        print(data[:10])
