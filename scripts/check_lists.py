#!/usr/bin/env python3
"""
Розширена перевірка списків доменів та регулярних виразів.

Скрипт перевіряє синтаксис, дублікати, перетини між файлами,
використовує метадані для виявлення неактивних записів і
може виконувати DNS-перевірки для моніторингових доменів.
"""

from __future__ import annotations

import re
import sys
import argparse
import socket
from pathlib import Path
from typing import Iterable

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
    """Повертає множину дублікатів у списку незалежно від регістру."""
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
    """Повертає список доменів, що не відповідають формату."""
    invalid = [d for d in domains if not DOMAIN_RE.fullmatch(d)]
    return invalid


def _validate_regexes(regexes: list[str]) -> list[str]:
    """Повертає список некоректних регулярних виразів."""
    invalid: list[str] = []
    for pattern in regexes:
        try:
            re.compile(pattern)
        except re.error:
            invalid.append(pattern)
    return invalid


def _find_cross_duplicates(domains: list[str], regexes: list[str]) -> set[str]:
    """Шукає однакові записи в domains.txt та regex.list."""
    return set(domains) & set(regexes)


def _validate_status(
    entries: Iterable[str],
    *,
    kind: str,
    catalog: Catalog,
) -> list[str]:
    """Перевіряє, чи є у каталозі записи зі статусом, відмінним від active."""

    mismatched: list[str] = []
    for item in entries:
        metadata = catalog.metadata_for(item, "domain" if kind == "domain" else "regex")
        if metadata and metadata.status != "active":
            mismatched.append(item)
    return mismatched


def _check_false_positives(domains: list[str], regexes: list[str], path: Path) -> list[str]:
    """Повертає повідомлення про присутність відомих хибнопозитивів."""

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
    """Перевіряє доступність доменів через DNS-запити."""

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


def main(argv: list[str] | None = None) -> int:
    """Головна функція перевірки списків."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--false-positives", type=Path, default=FALSE_POSITIVES_FILE)
    parser.add_argument("--check-dns", action="store_true")
    parser.add_argument("--dns-sample", type=int, default=20)
    args = parser.parse_args(argv)

    domains = load_entries(DOMAINS_FILE)
    regexes = load_entries(REGEX_FILE)
    catalog = load_catalog(args.catalog)

    issues: list[str] = []

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
