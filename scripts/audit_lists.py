#!/usr/bin/env python3
"""Створення аудиту списків доменів та регулярних виразів.

Generate audit reports for domain and regex blocklists.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:  # pragma: no cover - шлях для запуску напряму
    from .utils import Catalog, load_catalog, load_entries
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from scripts.utils import Catalog, load_catalog, load_entries

DOMAINS_FILE = Path("domains.txt")

REGEX_FILE = Path("regex.list")

CATALOG_FILE = Path("data/catalog.json")


def _find_duplicates(entries: list[str]) -> list[str]:
    """Повертає відсортований список дублікатів.

    Return a sorted list of duplicate entries.
    """

    counts = Counter(entries)
    duplicates = sorted(item for item, amount in counts.items() if amount > 1)
    return duplicates


def _status_breakdown(entries: list[str], *, kind: str, catalog: Catalog) -> tuple[Counter, set[str]]:
    """Підраховує кількість записів за статусами та повертає відсутні метадані.

    Count entries per status and collect values missing metadata.
    """

    statuses: Counter = Counter()
    missing: set[str] = set()
    for value in entries:
        metadata = catalog.metadata_for(value, kind)
        if metadata:
            statuses[metadata.status] += 1
        else:
            missing.add(value)
    return statuses, missing


def _summarize_collection(entries: list[str], *, kind: str, catalog: Catalog) -> dict[str, Any]:
    """Формує статистику для доменів або регулярних виразів.

    Build summary statistics for domains or regex lists.
    """

    duplicates = _find_duplicates(entries)
    unique_entries = sorted(set(entries))
    statuses, missing = _status_breakdown(unique_entries, kind=kind, catalog=catalog)
    total = len(entries)
    unique = len(unique_entries)
    with_metadata = unique - len(missing)
    coverage = (with_metadata / unique) if unique else 0.0
    summary: dict[str, Any] = {
        "total": total,
        "unique": unique,
        "duplicates": duplicates,
        "with_metadata": with_metadata,
        "coverage": round(coverage, 3),
        "missing_metadata": sorted(missing),
        "status_breakdown": dict(sorted(statuses.items())),
    }
    return summary


def _catalog_gaps(*, domains: list[str], regexes: list[str], catalog: Catalog, version: int | None) -> dict[str, Any]:
    """Повертає інформацію про записи каталогу без відповідників у списках.

    Describe catalog entries missing from generated blocklists.
    """

    domain_set = set(domains)
    regex_set = set(regexes)
    catalog_domains = set(catalog.domains.keys())
    catalog_regexes = set(catalog.regexes.keys())
    summary: dict[str, Any] = {
        "version": version,
        "domains_total": len(catalog_domains),
        "regexes_total": len(catalog_regexes),
        "orphan_domains": sorted(catalog_domains - domain_set),
        "orphan_regexes": sorted(catalog_regexes - regex_set),
    }
    return summary


def build_audit(domains: list[str], regexes: list[str], catalog: Catalog, *, version: int | None) -> dict[str, Any]:
    """Повертає повний аудит даних.

    Return a consolidated audit overview for domains, regexes, and catalog.
    """

    return {
        "domains": _summarize_collection(domains, kind="domain", catalog=catalog),
        "regexes": _summarize_collection(regexes, kind="regex", catalog=catalog),
        "catalog": _catalog_gaps(domains=domains, regexes=regexes, catalog=catalog, version=version),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI для формування аудиту.

    Command-line interface for generating the audit report.
    """

    parser = argparse.ArgumentParser(description="Аудит списків Pi-hole")
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--domains", type=Path, default=DOMAINS_FILE)
    parser.add_argument("--regex", type=Path, default=REGEX_FILE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    domains = load_entries(args.domains)
    regexes = load_entries(args.regex)
    catalog = load_catalog(args.catalog)
    raw_catalog = {}
    if args.catalog.exists():
        raw_catalog = json.loads(args.catalog.read_text() or "{}")
    version = raw_catalog.get("version") if isinstance(raw_catalog, dict) else None

    report = build_audit(domains, regexes, catalog, version=version if isinstance(version, int) else None)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)

    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover - ручний запуск
    raise SystemExit(main())
