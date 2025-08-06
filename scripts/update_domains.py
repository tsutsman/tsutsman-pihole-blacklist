#!/usr/bin/env python3
"""Завантажує домени з перевірених джерел і оновлює domains.txt."""
from __future__ import annotations

from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

CHUNK_SIZE = 500

DOMAINS_FILE = Path("domains.txt")
SOURCES = [
    "https://urlhaus.abuse.ch/downloads/hostfile/",
    "https://phishing.army/download/phishing_army_blocklist.txt",
    "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
    (
        "https://raw.githubusercontent.com/anudeepND/blacklist/"  # ad sources
        "master/adservers.txt"
    ),
    (
        "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/"
        "master/phishing-domains-ACTIVE.txt"
    ),
    (
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/"
        "alternates/gambling-only/hosts"
    ),
]


def _fetch(url: str) -> list[str]:
    """Завантажує домени з URL, повертаючи порожній список у разі помилки."""
    try:
        with urlopen(url, timeout=10) as resp:  # type: ignore[arg-type]
            text = resp.read().decode("utf-8", "replace")
    except URLError:
        return []
    domains: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        domain = parts[1] if len(parts) > 1 else parts[0]
        domains.append(domain.lower())
    return domains


def update(chunk_size: int = CHUNK_SIZE) -> None:
    """Оновлює файл доменів, додаючи нові записи з перевірених джерел."""
    existing = set()
    if DOMAINS_FILE.exists():
        existing = {
            line.strip()
            for line in DOMAINS_FILE.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        }

    fetched: set[str] = set()
    for url in SOURCES:
        fetched.update(_fetch(url))

    new_domains = sorted(fetched - existing)[:chunk_size]
    if not new_domains:
        return

    merged = sorted(existing | set(new_domains))
    DOMAINS_FILE.write_text("\n".join(merged) + "\n")


if __name__ == "__main__":
    update()
