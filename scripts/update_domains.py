"""Завантажує домени з перевірених джерел і оновлює domains.txt."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from ipaddress import ip_address
from http.client import IncompleteRead
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.parse import unquote
from urllib.request import urlopen

CHUNK_SIZE = 500

DOMAINS_FILE = Path("domains.txt")
_HOST_PREFIXES: tuple[str, ...] = (
    "0.0.0.0",
    "127.0.0.1",
    "255.255.255.255",
    "::",
    "::1",
)
SOURCES: tuple[str, ...] = (
    "https://urlhaus.abuse.ch/downloads/hostfile/",
    "https://phishing.army/download/phishing_army_blocklist.txt",
    "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
    "https://raw.githubusercontent.com/anudeepND/blacklist/master/adservers.txt",
    "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-domains-ACTIVE.txt",
    "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/gambling-only/hosts",
    "https://v.firebog.net/hosts/Prigent-Malware.txt",
    "https://v.firebog.net/hosts/Prigent-Crypto.txt",
    "https://raw.githubusercontent.com/PolishFiltersTeam/KADhosts/master/KADhosts.txt",
    "https://raw.githubusercontent.com/Spam404/lists/master/main-blacklist.txt",
    "https://malware-filter.gitlab.io/malware-filter/malware-filter-hosts.txt",
    "https://malware-filter.gitlab.io/malware-filter/phishing-filter-hosts.txt",
    "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/hosts/malicious.txt",
    "https://raw.githubusercontent.com/blocklistproject/Lists/master/malware.txt",
    "https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt",
)


def _clean_domain(raw: str) -> str | None:
    """Нормалізує значення домену, відкидаючи службові IP та коментарі."""
    domain = unquote(raw.split("#", 1)[0]).strip()
    if not domain:
        return None
    for prefix in _HOST_PREFIXES:
        if domain.startswith(prefix):
            domain = domain[len(prefix) :].strip()
    if domain.startswith("*."):
        domain = domain[2:]
    domain = domain.lstrip(".")
    domain = domain.rstrip("/")
    if not domain or domain.startswith("#"):
        return None
    try:
        ip_address(domain)
    except ValueError:
        cleaned = domain.lower().rstrip(".")
        return cleaned or None
    return None


def _fetch(url: str) -> list[str]:
    """Завантажує домени з URL, повертаючи порожній список у разі помилки."""
    try:
        with urlopen(url, timeout=10) as resp:  # type: ignore[arg-type]
            text = resp.read().decode("utf-8", "replace")
    except (URLError, IncompleteRead):
        return []
    domains: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        raw = parts[1] if len(parts) > 1 else parts[0]
        domain = _clean_domain(raw)
        if domain:
            domains.append(domain)
    return domains


def update(
    *,
    dest: Path = DOMAINS_FILE,
    chunk_size: int = CHUNK_SIZE,
    sources: Iterable[str] = SOURCES,
) -> None:
    """Оновлює файл доменів, додаючи нові записи з перевірених джерел."""
    existing: set[str] = set()
    needs_rewrite = False
    if dest.exists():
        for line in dest.read_text().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            domain = _clean_domain(stripped)
            if domain:
                if domain != stripped or domain in existing:
                    needs_rewrite = True
                existing.add(domain)
            else:
                needs_rewrite = True

    fetched: set[str] = set()
    with ThreadPoolExecutor() as pool:
        for domains in pool.map(_fetch, sources):
            fetched.update(domains)

    new_domains = sorted(fetched - existing)[:chunk_size]
    if new_domains:
        needs_rewrite = True
    if not new_domains and not needs_rewrite:
        return

    merged = sorted(existing | set(new_domains))
    dest.write_text("\n".join(merged) + "\n")


def main(argv: list[str] | None = None) -> None:
    """CLI-обгортка для оновлення списку доменів."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--dest", type=Path, default=DOMAINS_FILE)
    args = parser.parse_args(argv)
    update(dest=args.dest, chunk_size=args.chunk_size)


if __name__ == "__main__":
    main()
