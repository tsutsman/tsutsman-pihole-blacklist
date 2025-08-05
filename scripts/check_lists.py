#!/usr/bin/env python3
"""
Перевіряє списки доменів та регулярних виразів,
виявляє дублікати та некоректні записи.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOMAINS_FILE = Path("domains.txt")
REGEX_FILE = Path("regex.list")

DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*"
    r"\.[A-Za-z]{2,}$"
)


def _load_entries(path: Path) -> list[str]:
    entries: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def _find_duplicates(items: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return duplicates


def _validate_domains(domains: list[str]) -> list[str]:
    invalid = [d for d in domains if not DOMAIN_RE.fullmatch(d)]
    return invalid


def _validate_regexes(regexes: list[str]) -> list[str]:
    invalid: list[str] = []
    for pattern in regexes:
        try:
            re.compile(pattern)
        except re.error:
            invalid.append(pattern)
    return invalid


def main() -> int:
    domains = _load_entries(DOMAINS_FILE)
    regexes = _load_entries(REGEX_FILE)

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

    if issues:
        print("\n".join(issues))
        return 1

    print("Списки коректні")
    return 0


if __name__ == "__main__":
    sys.exit(main())
