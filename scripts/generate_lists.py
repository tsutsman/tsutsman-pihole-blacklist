#!/usr/bin/env python3
"""Генерує списки блокування у кількох форматах із підтримкою сегментації.

Generate blocklists in multiple formats with optional segmentation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

try:  # pragma: no cover
    from .utils import Catalog, EntryMetadata, load_catalog, load_entries
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from scripts.utils import Catalog, EntryMetadata, load_catalog, load_entries

DOMAINS_FILE = Path("domains.txt")
REGEX_FILE = Path("regex.list")
CATALOG_FILE = Path("data/catalog.json")
DIST_DIR = Path("dist")
AVAILABLE_FORMATS = ("adguard", "ublock", "hosts", "rpz", "dnsmasq", "unbound")
GROUP_CHOICES = ("category", "region", "source")
DEFAULT_SEGMENT_NAME = "без-метаданих"


def _slugify(value: str) -> str:
    normalized = value.lower()
    result: list[str] = []
    for char in normalized:
        if char.isalnum():
            result.append(char)
        elif char in {"-", "_"}:
            result.append(char)
        elif char in {" ", "/", "|", ":"}:
            result.append("-")
        else:
            result.append("-")
    slug = "".join(result).strip("-")
    return slug or "segment"


def _write_lines(path: Path, lines: Iterable[str]) -> None:
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content)


def _group_entries(
    entries: Sequence[tuple[str, EntryMetadata | None]],
    *,
    group_by: str | None,
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    if group_by is None:
        groups["усі"] = [value for value, _ in entries]
        return groups

    for value, metadata in entries:
        if metadata is None:
            groups[DEFAULT_SEGMENT_NAME].append(value)
            continue
        if group_by == "category":
            keys = [metadata.category] if getattr(metadata, "category", None) else [DEFAULT_SEGMENT_NAME]
        elif group_by == "region":
            regions = getattr(metadata, "regions", ()) or [DEFAULT_SEGMENT_NAME]
            keys = list(regions)
        else:
            sources = getattr(metadata, "sources", ()) or [DEFAULT_SEGMENT_NAME]
            keys = list(sources)
        for key in keys:
            groups[key].append(value)
    return groups


def _render_adblock(domains: Sequence[str], regexes: Sequence[str]) -> list[str]:
    return [f"||{d}^" for d in domains] + [f"/{r}/" for r in regexes]


def _render_hosts(domains: Sequence[str]) -> list[str]:
    return [f"0.0.0.0 {d}" for d in domains]


def _render_dnsmasq(domains: Sequence[str]) -> list[str]:
    return [f"address=/{d}/0.0.0.0" for d in domains]


def _render_unbound(domains: Sequence[str]) -> list[str]:
    return [f"local-zone: \"{d}\" static" for d in domains]


def _render_rpz(domains: Sequence[str]) -> list[str]:
    header = [
        "$TTL 300",
        "@ IN SOA localhost. hostmaster.localhost. (1 3600 600 86400 300)",
        "@ IN NS localhost.",
    ]
    records = [f"{d} CNAME ." for d in domains]
    return header + records


def _prepare_entries(
    catalog: Catalog,
    *,
    values: list[str],
    kind: str,
    categories: Sequence[str] | None,
    regions: Sequence[str] | None,
    sources: Sequence[str] | None,
    statuses: Sequence[str] | None,
    severities: Sequence[str] | None,
    tags: Sequence[str] | None,
) -> list[tuple[str, EntryMetadata | None]]:
    return list(
        catalog.iter_values_from(
            values,
            kind=kind,
            categories=categories,
            regions=regions,
            sources=sources,
            statuses=statuses,
            severities=severities,
            tags=tags,
            include_missing=True,
        )
    )


def generate(
    *,
    dist_dir: Path = DIST_DIR,
    formats: list[str] | None = None,
    catalog_path: Path = CATALOG_FILE,
    categories: Sequence[str] | None = None,
    regions: Sequence[str] | None = None,
    sources: Sequence[str] | None = None,
    statuses: Sequence[str] | None = None,
    include_inactive: bool = False,
    group_by: str | None = None,
    severities: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
) -> None:
    """Створює файли зі списками у вибраних форматах із фільтрами.

    Produce blocklists for selected formats while applying metadata filters.
    """

    catalog = load_catalog(catalog_path)
    domains_raw = load_entries(DOMAINS_FILE)
    regexes_raw = load_entries(REGEX_FILE)

    if statuses is None and not include_inactive:
        statuses = ["active"]

    domain_entries = _prepare_entries(
        catalog,
        values=domains_raw,
        kind="domain",
        categories=categories,
        regions=regions,
        sources=sources,
        statuses=statuses,
        severities=severities,
        tags=tags,
    )
    regex_entries = _prepare_entries(
        catalog,
        values=regexes_raw,
        kind="regex",
        categories=categories,
        regions=regions,
        sources=sources,
        statuses=statuses,
        severities=severities,
        tags=tags,
    )

    dist_dir.mkdir(exist_ok=True)

    if formats is None:
        formats = ["adguard", "ublock"]

    all_domains = [value for value, _ in domain_entries]
    all_regexes = [value for value, _ in regex_entries]

    domain_groups = _group_entries(domain_entries, group_by=group_by)
    regex_groups = _group_entries(regex_entries, group_by=group_by)

    for fmt in formats:
        if fmt == "adguard":
            lines = _render_adblock(all_domains, all_regexes)
            _write_lines(dist_dir / "adguard.txt", lines)
        elif fmt == "ublock":
            lines = _render_adblock(all_domains, all_regexes)
            _write_lines(dist_dir / "ublock.txt", lines)
        elif fmt == "hosts":
            _write_lines(dist_dir / "hosts.txt", _render_hosts(all_domains))
        elif fmt == "dnsmasq":
            _write_lines(dist_dir / "dnsmasq.conf", _render_dnsmasq(all_domains))
        elif fmt == "unbound":
            _write_lines(dist_dir / "unbound.conf", _render_unbound(all_domains))
        elif fmt == "rpz":
            _write_lines(dist_dir / "rpz.txt", _render_rpz(all_domains))

        if group_by is None:
            continue

        segment_dir = dist_dir / "segments" / group_by
        segment_dir.mkdir(parents=True, exist_ok=True)
        if fmt in {"adguard", "ublock"}:
            available_groups = set(domain_groups) | set(regex_groups)
        else:
            available_groups = set(domain_groups)
        for group in sorted(available_groups):
            domain_values = domain_groups.get(group, [])
            regex_values = regex_groups.get(group, [])
            if fmt in {"adguard", "ublock"}:
                lines = _render_adblock(domain_values, regex_values)
                filename = f"{fmt}--{_slugify(group)}.txt"
            elif fmt == "hosts":
                if not domain_values:
                    continue
                lines = _render_hosts(domain_values)
                filename = f"hosts--{_slugify(group)}.txt"
            elif fmt == "dnsmasq":
                if not domain_values:
                    continue
                lines = _render_dnsmasq(domain_values)
                filename = f"dnsmasq--{_slugify(group)}.conf"
            elif fmt == "unbound":
                if not domain_values:
                    continue
                lines = _render_unbound(domain_values)
                filename = f"unbound--{_slugify(group)}.conf"
            elif fmt == "rpz":
                if not domain_values:
                    continue
                lines = _render_rpz(domain_values)
                filename = f"rpz--{_slugify(group)}.txt"
            else:
                continue
            _write_lines(segment_dir / filename, lines)


def main(argv: list[str] | None = None) -> None:
    """CLI-обгортка для генерації списків.

    Command-line wrapper orchestrating blocklist generation.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=DIST_DIR)
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=AVAILABLE_FORMATS,
        default=None,
        help="Формати для генерації",
    )
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--categories", nargs="+")
    parser.add_argument("--regions", nargs="+")
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--statuses", nargs="+")
    parser.add_argument("--severities", nargs="+")
    parser.add_argument("--tags", nargs="+")
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument("--group-by", choices=GROUP_CHOICES)
    args = parser.parse_args(argv)

    generate(
        dist_dir=args.dist_dir,
        formats=args.formats,
        catalog_path=args.catalog,
        categories=args.categories,
        regions=args.regions,
        sources=args.sources,
        statuses=args.statuses,
        include_inactive=args.include_inactive,
        group_by=args.group_by,
        severities=args.severities,
        tags=args.tags,
    )


if __name__ == "__main__":
    main()
