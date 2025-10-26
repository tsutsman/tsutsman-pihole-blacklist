#!/usr/bin/env python3
"""Генерація агрегованих метрик для дашбордів і моніторингу.

Скрипт аналізує основні файли репозиторію (списки доменів та
регулярних виразів, каталог метаданих, звіти про оновлення
і журнал хибнопозитивів) та формує узагальнену статистику.
Результат можна використовувати для побудови зовнішніх
дашбордів або швидкого моніторингу змін у списках.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:  # pragma: no cover - забезпечує запуск як пакета і як модуля
    from .utils import (
        Catalog,
        EntryMetadata,
        FalsePositiveRecord,
        load_catalog,
        load_entries,
        load_false_positive_records,
    )
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from scripts.utils import (  # type: ignore
        Catalog,
        EntryMetadata,
        FalsePositiveRecord,
        load_catalog,
        load_entries,
        load_false_positive_records,
    )

DOMAINS_FILE = Path("domains.txt")
REGEX_FILE = Path("regex.list")
CATALOG_FILE = Path("data/catalog.json")
FALSE_POSITIVES_FILE = Path("data/false_positives.json")
LATEST_UPDATE_FILE = Path("reports/latest_update.json")
DASHBOARD_FILE = Path("reports/dashboard.json")
HISTORY_FILE = Path("reports/dashboard_history.json")


@dataclass(frozen=True)
class AggregatedCounters:
    """Зручний контейнер для зібраних лічильників."""

    categories: Counter[str]
    regions: Counter[str]
    severities: Counter[str]
    tags: Counter[str]
    sources: Counter[str]

    def as_dict(self) -> dict[str, dict[str, int]]:
        """Повертає словник зі згрупованими значеннями."""

        return {
            "categories": dict(self.categories),
            "regions": dict(self.regions),
            "severities": dict(self.severities),
            "tags": dict(self.tags),
            "sources": dict(self.sources),
        }


def _iter_present_metadata(
    entries: Iterable[str],
    *,
    catalog: Catalog,
    kind: str,
) -> Iterable[EntryMetadata]:
    """Ітерує метадані лише для записів, присутніх у списках."""

    for value in entries:
        metadata = catalog.metadata_for(value, kind)
        if metadata:
            yield metadata


def _aggregate_metadata(
    entries: Iterable[str],
    *,
    catalog: Catalog,
    kind: str,
) -> AggregatedCounters:
    """Формує лічильники категорій, регіонів, тегів тощо."""

    categories: Counter[str] = Counter()
    regions: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    sources: Counter[str] = Counter()

    for metadata in _iter_present_metadata(entries, catalog=catalog, kind=kind):
        categories[metadata.category] += 1
        for region in metadata.regions:
            regions[region] += 1
        if metadata.severity:
            severities[metadata.severity] += 1
        for tag in metadata.tags:
            tags[tag] += 1
        for source in metadata.sources:
            sources[source] += 1

    return AggregatedCounters(
        categories=categories,
        regions=regions,
        severities=severities,
        tags=tags,
        sources=sources,
    )


def _summarize_false_positives(
    records: list[FalsePositiveRecord],
) -> dict[str, Any]:
    """Повертає агреговану статистику за зверненнями хибнопозитивів."""

    status_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()

    for record in records:
        status = record.review_status or "невідомо"
        status_counter[status] += 1
        action = record.action or "без дії"
        action_counter[action] += 1

    return {
        "total": len(records),
        "by_status": dict(status_counter),
        "by_action": dict(action_counter),
    }


def load_json_or_default(path: Path, default: Any) -> Any:
    """Завантажує JSON або повертає значення за замовчуванням."""

    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    return json.loads(text)


def build_dashboard(
    *,
    domains_path: Path = DOMAINS_FILE,
    regex_path: Path = REGEX_FILE,
    catalog_path: Path = CATALOG_FILE,
    false_positive_path: Path = FALSE_POSITIVES_FILE,
    latest_update_path: Path = LATEST_UPDATE_FILE,
) -> dict[str, Any]:
    """Формує словник із метриками дашборду."""

    domains = load_entries(domains_path)
    regexes = load_entries(regex_path)
    catalog = load_catalog(catalog_path)
    domain_records, regex_records = load_false_positive_records(false_positive_path)
    latest_update = load_json_or_default(latest_update_path, {})

    total_domains = len(domains)
    total_regexes = len(regexes)

    domain_with_metadata = sum(1 for value in domains if value in catalog.domains)
    regex_with_metadata = sum(1 for value in regexes if value in catalog.regexes)

    monitored_domains = sum(
        1
        for value in domains
        if (metadata := catalog.metadata_for(value, "domain")) and metadata.monitor
    )

    severity_counter = Counter()
    for metadata in _iter_present_metadata(domains, catalog=catalog, kind="domain"):
        if metadata.severity:
            severity_counter[metadata.severity] += 1

    dashboard: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "domains": total_domains,
            "regexes": total_regexes,
        },
        "metadata": {
            "domains": {
                "with_metadata": domain_with_metadata,
                "without_metadata": total_domains - domain_with_metadata,
                "coverage_pct": round(
                    (domain_with_metadata / total_domains * 100) if total_domains else 0,
                    2,
                ),
            },
            "regexes": {
                "with_metadata": regex_with_metadata,
                "without_metadata": total_regexes - regex_with_metadata,
                "coverage_pct": round(
                    (regex_with_metadata / total_regexes * 100) if total_regexes else 0,
                    2,
                ),
            },
        },
        "monitored": {
            "domains": monitored_domains,
        },
        "domains": _aggregate_metadata(domains, catalog=catalog, kind="domain").as_dict(),
        "regexes": _aggregate_metadata(regexes, catalog=catalog, kind="regex").as_dict(),
        "severity_distribution": dict(severity_counter),
        "false_positives": {
            "domains": _summarize_false_positives(domain_records),
            "regexes": _summarize_false_positives(regex_records),
        },
    }

    if latest_update:
        added = latest_update.get("added", []) or []
        stale = latest_update.get("stale_candidates", []) or []
        dashboard["latest_update"] = {
            "generated_at": latest_update.get("generated_at"),
            "total_after_update": latest_update.get("total_after_update"),
            "added_count": len(added),
            "stale_candidates_count": len(stale),
            "source_health": latest_update.get("source_health"),
        }

    return dashboard


def update_history(
    path: Path,
    snapshot: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Додає знімок метрик до історії, обрізаючи її до ліміту."""

    if limit < 1:
        raise ValueError("Ліміт історії має бути додатним")

    raw_history = load_json_or_default(path, [])
    if not isinstance(raw_history, list):
        raise TypeError("Історія має бути списком")

    entry = {
        "generated_at": snapshot.get("generated_at"),
        "totals": snapshot.get("totals", {}),
        "metadata": snapshot.get("metadata", {}),
        "monitored": snapshot.get("monitored", {}),
    }

    raw_history.append(entry)
    trimmed = raw_history[-limit:]
    path.write_text(json.dumps(trimmed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return trimmed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Формування агрегованої аналітики для дашборду",
    )
    parser.add_argument("--domains", type=Path, default=DOMAINS_FILE)
    parser.add_argument("--regexes", type=Path, default=REGEX_FILE)
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--false-positives", type=Path, default=FALSE_POSITIVES_FILE)
    parser.add_argument("--latest-update", type=Path, default=LATEST_UPDATE_FILE)
    parser.add_argument("--dashboard", type=Path, default=DASHBOARD_FILE)
    parser.add_argument("--history", type=Path, default=HISTORY_FILE)
    parser.add_argument(
        "--history-limit",
        type=int,
        default=90,
        help="Кількість знімків, що зберігатимуться в історії",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Не оновлювати історичний файл",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    snapshot = build_dashboard(
        domains_path=args.domains,
        regex_path=args.regexes,
        catalog_path=args.catalog,
        false_positive_path=args.false_positives,
        latest_update_path=args.latest_update,
    )

    args.dashboard.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if not args.skip_history:
        update_history(args.history, snapshot, limit=args.history_limit)

    print(json.dumps(snapshot, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - ручний запуск
    raise SystemExit(main())
