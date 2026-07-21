from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Mapping


HYMN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class CatalogEntry:
    hymn_id: str
    title: str
    source_path: str
    score_sha256: str | None = None
    original_key: str | None = None
    available_lines: tuple[str, ...] = ("SATB", "S", "A", "T", "B")
    lyrics_scope: str | None = None
    rights_status: str | None = None


class CatalogSourceUnavailable(FileNotFoundError):
    """Raised when a fixed catalog record has no valid deployed source."""


class CatalogConfigurationError(ValueError):
    """Raised when the canonical catalog is invalid or path-unsafe."""


class UnknownHymnId(KeyError):
    """Raised when a request names an id absent from the fixed catalog."""


def default_catalog_path() -> Path:
    configured = os.environ.get("HYMNS_CATALOG_PATH")
    if configured:
        return Path(configured)
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / "catalog" / "catalog.json"


def default_catalog_root() -> Path:
    configured = os.environ.get("HYMNS_CATALOG_ROOT")
    if configured:
        return Path(configured)
    return default_catalog_path().parent


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_entries(catalog_path: Path) -> tuple[CatalogEntry, ...]:
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogConfigurationError(
            f"Could not read canonical catalog at {catalog_path}."
        ) from exc
    try:
        items = payload["items"]
        if not isinstance(items, list):
            raise TypeError
        entries = tuple(
            CatalogEntry(
                hymn_id=item["id"],
                title=item["title"],
                source_path=item["score"]["path"],
                score_sha256=item["score"]["sha256"],
                original_key=item["original_key"]["name"],
                available_lines=tuple(item["available_lines"]),
                lyrics_scope=item["lyrics"]["scope"],
                rights_status=item["rights"]["status"],
            )
            for item in items
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogConfigurationError(
            "Canonical catalog records do not match the render service contract."
        ) from exc

    return entries


class HymnCatalog:
    def __init__(
        self,
        root: Path | None = None,
        entries: tuple[CatalogEntry, ...] | None = None,
        catalog_path: Path | None = None,
    ) -> None:
        if entries is None:
            entries = _load_entries((catalog_path or default_catalog_path()).resolve())
        self.root = (root or default_catalog_root()).resolve()
        self._entries: Mapping[str, CatalogEntry] = {
            entry.hymn_id: entry for entry in entries
        }
        if len(self._entries) != len(entries):
            raise CatalogConfigurationError("Catalog hymn ids must be unique.")
        if any(not HYMN_ID_RE.fullmatch(entry.hymn_id) for entry in entries):
            raise CatalogConfigurationError("Catalog hymn ids must be stable slugs.")

    def entries(self) -> tuple[CatalogEntry, ...]:
        return tuple(self._entries.values())

    def entry(self, hymn_id: str) -> CatalogEntry:
        try:
            return self._entries[hymn_id]
        except KeyError as exc:
            raise UnknownHymnId(hymn_id) from exc

    def source_available(self, hymn_id: str) -> bool:
        try:
            self.resolve_source(hymn_id)
        except (CatalogSourceUnavailable, CatalogConfigurationError, UnknownHymnId):
            return False
        return True

    def resolve_source(self, hymn_id: str) -> Path:
        entry = self.entry(hymn_id)
        candidate = (self.root / entry.source_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise CatalogConfigurationError(
                f"Catalog source for {hymn_id!r} escapes the catalog root."
            ) from exc
        if not candidate.is_file():
            raise CatalogSourceUnavailable(
                f"MusicXML source for {hymn_id!r} is not deployed."
            )
        if entry.score_sha256 and _sha256_file(candidate) != entry.score_sha256:
            raise CatalogSourceUnavailable(
                f"MusicXML source for {hymn_id!r} failed its catalog hash."
            )
        return candidate
