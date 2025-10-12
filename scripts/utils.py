"""Допоміжні функції для роботи зі списками та метаданими."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


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
        severities: Sequence[str] | None = None,
        tags: Sequence[str] | None = None,
    ) -> bool:
        """Перевіряє, чи відповідає запис заданим фільтрам."""

        if categories and self.category not in categories:
            return False
        if statuses and self.status not in statuses:
            return False
        if severities:
            if not self.severity or self.severity not in severities:
                return False
        if regions and not set(self.regions) & set(regions):
            return False
        if sources and not set(self.sources) & set(sources):
            return False
        if tags and not set(self.tags) & set(tags):
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
        severities: Sequence[str] | None = None,
        tags: Sequence[str] | None = None,
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
                    severities=severities,
                    tags=tags,
                ):
                    yield value, metadata
            elif (
                include_missing
                and not categories
                and not regions
                and not sources
                and not severities
                and not tags
                and (not statuses or "active" in statuses)
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


@dataclass(frozen=True)
class FalsePositiveRecord:
    """Опис звернення щодо хибнопозитивного запису."""

    value: str
    original_value: str | None = None
    reason: str | None = None
    reported_by: str | None = None
    reported_at: str | None = None
    review_status: str | None = None
    action: str | None = None
    notes: str | None = None
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Перетворює запис на словник для звітів."""

        data: dict[str, Any] = {"value": self.display_value}
        if self.reason:
            data["reason"] = self.reason
        if self.reported_by:
            data["reported_by"] = self.reported_by
        if self.reported_at:
            data["reported_at"] = self.reported_at
        if self.review_status:
            data["review_status"] = self.review_status
        if self.action:
            data["action"] = self.action
        if self.notes:
            data["notes"] = self.notes
        if self.evidence:
            data["evidence"] = list(self.evidence)
        return data

    @property
    def display_value(self) -> str:
        """Повертає людинозрозумілу форму значення."""

        return self.original_value or self.value


def _normalize_optional(value: Any) -> str | None:
    """Повертає очищений рядок або None."""

    if value is None:
        return None
    string = str(value).strip()
    return string or None


def _load_false_positive_records(
    raw_entries: Iterable[Any],
    *,
    lower_value: bool,
) -> list[FalsePositiveRecord]:
    """Перетворює записи хибнопозитивів на об'єкти."""

    records: list[FalsePositiveRecord] = []
    for raw in raw_entries:
        if isinstance(raw, str):
            value = raw.strip()
            if not value:
                continue
            normalized = value.lower() if lower_value else value
            records.append(FalsePositiveRecord(value=normalized, original_value=value))
            continue

        if isinstance(raw, Mapping):
            original = _normalize_optional(raw.get("value"))
            if not original:
                continue
            normalized = original.lower() if lower_value else original
            evidence = tuple(
                str(item).strip()
                for item in raw.get("evidence", [])
                if str(item).strip()
            )
            records.append(
                FalsePositiveRecord(
                    value=normalized,
                    original_value=original,
                    reason=_normalize_optional(raw.get("reason")),
                    reported_by=_normalize_optional(raw.get("reported_by")),
                    reported_at=_normalize_optional(raw.get("reported_at")),
                    review_status=_normalize_optional(raw.get("review_status")),
                    action=_normalize_optional(raw.get("action")),
                    notes=_normalize_optional(raw.get("notes")),
                    evidence=evidence,
                )
            )
    return records


def load_false_positive_records(
    path: Path,
) -> tuple[list[FalsePositiveRecord], list[FalsePositiveRecord]]:
    """Завантажує звернення щодо хибнопозитивів для доменів та regex."""

    if not path.exists():
        return [], []
    data = json.loads(path.read_text() or "{}")
    domain_records = _load_false_positive_records(
        data.get("domains", []),
        lower_value=True,
    )
    regex_records = _load_false_positive_records(
        data.get("regexes", []),
        lower_value=False,
    )
    return domain_records, regex_records


def load_false_positive_lists(path: Path) -> tuple[set[str], set[str]]:
    """Повертає множини значень, позначених як хибнопозитиви."""

    domain_records, regex_records = load_false_positive_records(path)
    domains = {record.value for record in domain_records}
    regexes = {record.value for record in regex_records}
    return domains, regexes
