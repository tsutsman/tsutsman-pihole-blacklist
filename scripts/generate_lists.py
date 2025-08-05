#!/usr/bin/env python3
"""
Генерує списки у форматах AdGuard та uBlock
з файлів domains.txt та regex.list.
"""

from __future__ import annotations

from pathlib import Path

DOMAINS_FILE = Path("domains.txt")
REGEX_FILE = Path("regex.list")
DIST_DIR = Path("dist")


def _load_entries(path: Path) -> list[str]:
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def generate() -> None:
    domains = _load_entries(DOMAINS_FILE)
    regexes = _load_entries(REGEX_FILE)

    DIST_DIR.mkdir(exist_ok=True)

    adguard = [f"||{d}^" for d in domains] + [f"/{r}/" for r in regexes]
    (DIST_DIR / "adguard.txt").write_text("\n".join(adguard) + "\n")

    ublock = adguard  # для простоти формати однакові
    (DIST_DIR / "ublock.txt").write_text("\n".join(ublock) + "\n")


if __name__ == "__main__":
    generate()
