#!/usr/bin/env python3
"""Генерує списки у форматах AdGuard, uBlock та hosts."""

from __future__ import annotations

import argparse
from pathlib import Path

from .utils import load_entries

DOMAINS_FILE = Path("domains.txt")
REGEX_FILE = Path("regex.list")
DIST_DIR = Path("dist")
AVAILABLE_FORMATS = ("adguard", "ublock", "hosts")


def generate(
    dist_dir: Path = DIST_DIR,
    formats: list[str] | None = None,
) -> None:
    """Створює файли зі списками у вибраних форматах."""
    domains = load_entries(DOMAINS_FILE)
    regexes = load_entries(REGEX_FILE)

    dist_dir.mkdir(exist_ok=True)

    if formats is None:
        formats = ["adguard", "ublock"]

    base = [f"||{d}^" for d in domains] + [f"/{r}/" for r in regexes]

    if "adguard" in formats:
        (dist_dir / "adguard.txt").write_text("\n".join(base) + "\n")

    if "ublock" in formats:
        (dist_dir / "ublock.txt").write_text("\n".join(base) + "\n")

    if "hosts" in formats:
        hosts = [f"0.0.0.0 {d}" for d in domains]
        (dist_dir / "hosts.txt").write_text("\n".join(hosts) + "\n")


def main(argv: list[str] | None = None) -> None:
    """CLI-обгортка для генерації списків."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=DIST_DIR)
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=AVAILABLE_FORMATS,
        default=None,
        help="Формати для генерації",
    )
    args = parser.parse_args(argv)
    generate(dist_dir=args.dist_dir, formats=args.formats)


if __name__ == "__main__":
    main()
