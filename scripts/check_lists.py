#!/usr/bin/env python3
"""
Перевіряє списки доменів та регулярних виразів,
виявляє дублікати та некоректні записи.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .utils import load_entries

DOMAINS_FILE = Path("domains.txt")

REGEX_FILE = Path("regex.list")

DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*"
    r"\.[A-Za-z]{2,}$"
)


def _find_duplicates(items: list[str]) -> set[str]:
    """Повертає множину дублікатів у списку."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
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


def main() -> int:
    """Головна функція перевірки списків."""
    domains = load_entries(DOMAINS_FILE)
    regexes = load_entries(REGEX_FILE)

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

    if issues:
        print("\n".join(issues))
        return 1

    print("Списки коректні")
    return 0


if __name__ == "__main__":
    sys.exit(main())
