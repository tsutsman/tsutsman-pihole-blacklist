"""Допоміжні функції для роботи зі списками та метаданими."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence


def load_entries(path: Path) -> list[str]:
    """Читає файл, повертаючи лише непорожні рядки без коментарів."""
    entries: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line.lower())
    return entries


@dataclass(frozen=True)
class EntryMetadata:
    """Метадані про домен або регулярний вираз."""

    value: str
    category: str = "інше"
    regions: tuple[str, ...] = ("global",)
    sources: tuple[str, ...] = ()
    added: str | None = None
    severity: str | None = None
    status: str = "active"
    monitor: bool = False
    tags: tuple[str, ...] = ()
    notes: str | None = None

    def matches(
        self,
        *,
        categories: Sequence[str] | None = None,
        regions: Sequence[str] | None = None,
        sources: Sequence[str] | None = None,
        statuses: Sequence[str] | None = None,
    ) -> bool:
        """Перевіряє, чи відповідає запис заданим фільтрам."""

        if categories and self.category not in categories:
            return False
        if statuses and self.status not in statuses:
            return False
        if regions and not set(self.regions) & set(regions):
            return False
        if sources and not set(self.sources) & set(sources):
            return False
        return True


@dataclass
class Catalog:
    """Каталог доменів та регулярних виразів із метаданими."""

    domains: Mapping[str, EntryMetadata]
    regexes: Mapping[str, EntryMetadata]

    def metadata_for(self, value: str, kind: str) -> EntryMetadata | None:
        """Повертає метадані для конкретного значення."""

        normalized = value.lower()
        lookup = self.domains if kind == "domain" else self.regexes
        return lookup.get(normalized)

    def iter_values_from(
        self,
        values: Iterable[str],
        *,
        kind: str,
        categories: Sequence[str] | None = None,
        regions: Sequence[str] | None = None,
        sources: Sequence[str] | None = None,
        statuses: Sequence[str] | None = None,
        include_missing: bool = True,
    ) -> Iterator[tuple[str, EntryMetadata | None]]:
        """Ітерує передані значення з урахуванням фільтрів."""

        for value in values:
            metadata = self.metadata_for(value, "domain" if kind == "domain" else "regex")
            if metadata:
                if metadata.matches(
                    categories=categories,
                    regions=regions,
                    sources=sources,
                    statuses=statuses,
                ):
                    yield value, metadata
            elif include_missing and not categories and not regions and not sources and (
                not statuses or "active" in statuses
            ):
                yield value, None


def _load_metadata_collection(data: Iterable[Mapping[str, object]], *, lower: bool) -> dict[str, EntryMetadata]:
    """Перетворює необроблені словники метаданих на об'єкти."""

    collection: dict[str, EntryMetadata] = {}
    for raw in data:
        value = str(raw.get("value", "")).strip()
        if not value:
            continue
        key = value.lower() if lower else value
        collection[key] = EntryMetadata(
            value=key,
            category=str(raw.get("category", "інше")),
            regions=tuple(str(item) for item in raw.get("regions", ["global"])),
            sources=tuple(str(item) for item in raw.get("sources", [])),
            added=str(raw.get("added")) if raw.get("added") else None,
            severity=str(raw.get("severity")) if raw.get("severity") else None,
            status=str(raw.get("status", "active")),
            monitor=bool(raw.get("monitor", False)),
            tags=tuple(str(item) for item in raw.get("tags", [])),
            notes=str(raw.get("notes")) if raw.get("notes") else None,
        )
    return collection


def load_catalog(path: Path) -> Catalog:
    """Завантажує каталог метаданих із JSON-файла."""

    if not path.exists():
        return Catalog(domains={}, regexes={})
    data = json.loads(path.read_text() or "{}")
    domain_meta = _load_metadata_collection(data.get("domains", []), lower=True)
    regex_meta = _load_metadata_collection(data.get("regexes", []), lower=True)
    return Catalog(domains=domain_meta, regexes=regex_meta)


def load_false_positive_lists(path: Path) -> tuple[set[str], set[str]]:
    """Повертає списки потенційних хибнопозитивних записів."""

    if not path.exists():
        return set(), set()
    data = json.loads(path.read_text() or "{}")
    domains = {str(item).lower() for item in data.get("domains", [])}
    regexes = {str(item) for item in data.get("regexes", [])}
    return domains, regexes
