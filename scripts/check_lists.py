#!/usr/bin/env python3
"""
Розширена перевірка списків доменів та регулярних виразів.

Extended validation of domain and regular-expression blocklists.

Скрипт перевіряє синтаксис, дублікати, перетини між файлами,
використовує метадані для виявлення неактивних записів і
може виконувати DNS-перевірки для моніторингових доменів.

The script validates syntax, detects duplicates and overlaps, leverages
metadata to highlight inactive entries, and can run DNS checks for entries
marked for monitoring.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:  # pragma: no cover - шлях для запуску напряму
    from .utils import Catalog, EntryMetadata, load_catalog, load_entries, load_false_positive_lists
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from scripts.utils import Catalog, EntryMetadata, load_catalog, load_entries, load_false_positive_lists

DOMAINS_FILE = Path("domains.txt")

REGEX_FILE = Path("regex.list")

CATALOG_FILE = Path("data/catalog.json")

FALSE_POSITIVES_FILE = Path("data/false_positives.json")

DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*"
    r"\.[A-Za-z]{2,}$"
)


def _find_duplicates(items: list[str]) -> set[str]:
    """Повертає множину дублікатів у списку незалежно від регістру.

    Return the set of duplicated entries ignoring case sensitivity.
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        key = item.lower()
        if key in seen:
            duplicates.add(item)
        else:
            seen.add(key)
    return duplicates


def _validate_domains(domains: list[str]) -> list[str]:
    """Повертає список доменів, що не відповідають формату.

    Return a list of domains that fail the validation pattern.
    """
    invalid = [d for d in domains if not DOMAIN_RE.fullmatch(d)]
    return invalid


def _validate_regexes(regexes: list[str]) -> list[str]:
    """Повертає список некоректних регулярних виразів.

    Return the list of malformed regular-expression patterns.
    """
    invalid: list[str] = []
    for pattern in regexes:
        try:
            re.compile(pattern)
        except re.error:
            invalid.append(pattern)
    return invalid


def _find_cross_duplicates(domains: list[str], regexes: list[str]) -> set[str]:
    """Шукає однакові записи в domains.txt та regex.list.

    Identify entries that appear in both domains.txt and regex.list.
    """
    return set(domains) & set(regexes)


def _find_missing_metadata(
    entries: Iterable[str],
    *,
    kind: str,
    catalog: Catalog,
) -> list[str]:
    """Повертає відсортований список записів без метаданих у каталозі.

    Return a sorted list of entries that lack catalog metadata.
    """

    missing: set[str] = set()
    for item in entries:
        if not catalog.metadata_for(item, kind):
            missing.add(item)
    return sorted(missing)


def _validate_status(
    entries: Iterable[str],
    *,
    kind: str,
    catalog: Catalog,
) -> list[str]:
    """Перевіряє, чи є у каталозі записи зі статусом, відмінним від active.

    Check whether catalog metadata marks any entry as non-active.
    """

    mismatched: list[str] = []
    for item in entries:
        metadata = catalog.metadata_for(item, "domain" if kind == "domain" else "regex")
        if metadata and metadata.status != "active":
            mismatched.append(item)
    return mismatched


def _check_false_positives(domains: list[str], regexes: list[str], path: Path) -> list[str]:
    """Повертає повідомлення про присутність відомих хибнопозитивів.

    Return messages describing entries flagged as known false positives.
    """

    fp_domains, fp_regexes = load_false_positive_lists(path)
    issues: list[str] = []
    present_domains = sorted(set(domains) & fp_domains)
    if present_domains:
        issues.append(
            "Ймовірні хибнопозитивні домени: " + ", ".join(present_domains)
        )
    present_regexes = sorted(set(regexes) & fp_regexes)
    if present_regexes:
        issues.append(
            "Ймовірні хибнопозитивні регулярні вирази: " + ", ".join(present_regexes)
        )
    return issues


def _check_dns(domains: list[str], *, catalog: Catalog, limit: int) -> list[str]:
    """Перевіряє доступність доменів через DNS-запити.

    Probe domain availability using DNS lookups for a limited sample.
    """

    monitored = [d for d in domains if (catalog.metadata_for(d, "domain") or EntryMetadata(value=d)).monitor]
    if monitored:
        sample = monitored[:limit]
    else:
        sample = domains[:limit]
    if not sample:
        return []

    failed: list[str] = []
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(2)
    try:
        for domain in sample:
            try:
                socket.getaddrinfo(domain, None)
            except socket.gaierror:
                failed.append(domain)
            except socket.timeout:
                failed.append(domain)
    finally:
        socket.setdefaulttimeout(previous_timeout)
    return failed


def _find_incomplete_metadata(
    raw_entries: Iterable[Mapping[str, Any]],
    *,
    required_fields: Sequence[str],
) -> list[str]:
    """Шукає активні записи каталогу без обов'язкових полів."""

    issues: list[str] = []
    for raw in raw_entries:
        if not isinstance(raw, Mapping):
            continue
        raw_status = raw.get("status")
        status_value = str(raw_status).strip().lower() if raw_status is not None else None
        is_active = status_value in (None, "", "active")
        if not is_active:
            continue

        missing: list[str] = []
        for field in required_fields:
            if field not in raw:
                missing.append(field)
                continue
            value = raw[field]
            if field in {"category", "status"}:
                if not str(value).strip():
                    missing.append(field)
            elif field in {"regions", "sources"}:
                if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not list(value):
                    missing.append(field)
        if missing:
            display_value = str(raw.get("value", "")).strip() or "<невідомий>"
            issues.append(f"{display_value}: {', '.join(sorted(set(missing)))}")
    return issues


def main(argv: list[str] | None = None) -> int:
    """Головна функція перевірки списків.

    Primary entry point coordinating blocklist validation tasks.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--false-positives", type=Path, default=FALSE_POSITIVES_FILE)
    parser.add_argument("--check-dns", action="store_true")
    parser.add_argument("--dns-sample", type=int, default=20)
    parser.add_argument(
        "--require-metadata",
        action="append",
        choices=("domains", "regexes", "all"),
        help=(
            "Вимагати наявність метаданих для доменів, регулярних виразів або обох списків. "
            "Параметр можна повторювати."
        ),
    )
    args = parser.parse_args(argv)

    domains = load_entries(DOMAINS_FILE)
    regexes = load_entries(REGEX_FILE)
    catalog = load_catalog(args.catalog)

    raw_catalog: dict[str, Any] = {}
    if args.catalog.exists():
        raw_catalog = json.loads(args.catalog.read_text() or "{}")


    issues: list[str] = []

    required_metadata: set[str] = set()
    if args.require_metadata:
        for requirement in args.require_metadata:
            if requirement == "all":
                required_metadata.update({"domains", "regexes"})
            else:
                required_metadata.add(str(requirement))

    duplicates = _find_duplicates(domains)
    if duplicates:
        duplicates_list = ", ".join(sorted(duplicates))
        issues.append(f"Дублікати у domains.txt: {duplicates_list}")

    invalid_domains = _validate_domains(domains)
    if invalid_domains:
        invalid_domains_list = ", ".join(sorted(invalid_domains))
        issues.append(f"Некоректні домени: {invalid_domains_list}")

    duplicates = _find_duplicates(regexes)
    if duplicates:
        regex_duplicates_list = ", ".join(sorted(duplicates))
        issues.append(f"Дублікати у regex.list: {regex_duplicates_list}")

    invalid_regexes = _validate_regexes(regexes)
    if invalid_regexes:
        invalid_regex_list = ", ".join(sorted(invalid_regexes))
        issues.append(f"Некоректні регулярні вирази: {invalid_regex_list}")

    cross_duplicates = _find_cross_duplicates(domains, regexes)
    if cross_duplicates:
        cross_list = ", ".join(sorted(cross_duplicates))
        message = f"Записи в обох списках: {cross_list}"
        issues.append(message)

    inactive_domains = _validate_status(domains, kind="domain", catalog=catalog)
    if inactive_domains:
        issues.append(
            "Домени зі статусом, відмінним від active у каталозі: "
            + ", ".join(sorted(inactive_domains))
        )

    inactive_regexes = _validate_status(regexes, kind="regex", catalog=catalog)
    if inactive_regexes:
        issues.append(
            "Регулярні вирази зі статусом, відмінним від active у каталозі: "
            + ", ".join(sorted(inactive_regexes))
        )

    if "domains" in required_metadata:
        missing_domains = _find_missing_metadata(domains, kind="domain", catalog=catalog)
        if missing_domains:
            issues.append(
                "Домени без метаданих у каталозі: " + ", ".join(missing_domains)
            )

    if "regexes" in required_metadata:
        missing_regexes = _find_missing_metadata(regexes, kind="regex", catalog=catalog)
        if missing_regexes:
            issues.append(
                "Регулярні вирази без метаданих у каталозі: "
                + ", ".join(missing_regexes)
            )

    required_fields = ("category", "regions", "sources", "status")
    incomplete_domains = _find_incomplete_metadata(
        raw_catalog.get("domains", []),
        required_fields=required_fields,
    )
    if incomplete_domains:
        issues.append(
            "Домени з неповними метаданими (потрібні category, regions, sources, status): "
            + "; ".join(sorted(incomplete_domains))
        )

    incomplete_regexes = _find_incomplete_metadata(
        raw_catalog.get("regexes", []),
        required_fields=required_fields,
    )
    if incomplete_regexes:
        issues.append(
            "Регулярні вирази з неповними метаданими (потрібні category, regions, sources, status): "
            + "; ".join(sorted(incomplete_regexes))
        )

    issues.extend(_check_false_positives(domains, regexes, args.false_positives))

    if args.check_dns:
        failed = _check_dns(domains, catalog=catalog, limit=args.dns_sample)
        if failed:
            issues.append(
                "Домени без DNS-відповіді: " + ", ".join(sorted(set(failed)))
            )

    if issues:
        print("\n".join(issues))
        return 1

    print("Списки коректні")
    return 0


if __name__ == "__main__":
    sys.exit(main())
