#!/usr/bin/env python3
"""Завантажує домени з перевірених джерел і оновлює domains.txt."""
from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

DOMAINS_FILE = Path("domains.txt")
SOURCES = [
    "https://urlhaus.abuse.ch/downloads/hostfile/",
    "https://phishing.army/download/phishing_army_blocklist.txt",
    "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
]


def _fetch(url: str) -> list[str]:
    with urlopen(url) as resp:  # type: ignore[arg-type]
        text = resp.read().decode("utf-8", "replace")
    domains: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        domain = parts[1] if len(parts) > 1 else parts[0]
        domains.append(domain.lower())
    return domains


def update() -> None:
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

    merged = sorted(existing | fetched)
    DOMAINS_FILE.write_text("\n".join(merged) + "\n")


if __name__ == "__main__":
    update()
