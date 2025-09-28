"""Завантажує домени з перевірених джерел і оновлює domains.txt."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import ip_address
from http.client import IncompleteRead
import time
from pathlib import Path
from typing import Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import urlopen

CHUNK_SIZE = 2000
MAX_PARALLEL_FETCHES = 4
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

DOMAINS_FILE = Path("domains.txt")
CONFIG_FILE = Path("data/sources.json")
REPORT_FILE = Path("reports/latest_update.json")
STATUS_FILE = Path("data/domain_status.json")
_HOST_PREFIXES: tuple[str, ...] = (
    "0.0.0.0",
    "127.0.0.1",
    "255.255.255.255",
    "::",
    "::1",
)


@dataclass(frozen=True)
class SourceConfig:
    """Опис джерела доменів."""

    name: str
    url: str
    category: str = "загальна"
    regions: tuple[str, ...] = ("global",)
    weight: float = 1.0
    update_interval_days: int = 1
    enabled: bool = True
    notes: str | None = None


def _load_sources(path: Path) -> list[SourceConfig]:
    """Завантажує конфігурацію джерел з JSON-файла."""

    if not path.exists():
        return []
    data = json.loads(path.read_text() or "{}")
    sources: list[SourceConfig] = []
    for item in data.get("sources", []):
        url = str(item.get("url", "")).strip()
        name = str(item.get("name", url or "невідоме джерело")).strip()
        if not url:
            continue
        sources.append(
            SourceConfig(
                name=name,
                url=url,
                category=str(item.get("category", "загальна")),
                regions=tuple(str(region) for region in item.get("regions", ["global"])),
                weight=float(item.get("weight", 1.0)),
                update_interval_days=int(item.get("update_interval_days", 1)),
                enabled=bool(item.get("enabled", True)),
                notes=str(item.get("notes")) if item.get("notes") else None,
            )
        )
    return sources


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


def _retry_delay(base_delay: float, error: HTTPError) -> float:
    """Обчислює затримку перед повтором запиту."""

    header = getattr(error, "headers", None)
    if header:
        retry_after = header.get("Retry-After")
        if retry_after:
            try:
                parsed = float(retry_after)
            except ValueError:
                pass
            else:
                return max(parsed, base_delay)
    return base_delay


def _read_source(url: str) -> str | None:
    """Завантажує вміст джерела з повторними спробами при тимчасових помилках."""

    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(url, timeout=10) as resp:  # type: ignore[arg-type]
                return resp.read().decode("utf-8", "replace")
        except HTTPError as error:
            if error.code not in RETRYABLE_STATUS or attempt + 1 >= MAX_RETRIES:
                return None
            delay = _retry_delay(delay, error)
            time.sleep(delay)
            delay *= 2
        except (URLError, IncompleteRead):
            if attempt + 1 >= MAX_RETRIES:
                return None
            time.sleep(delay)
            delay *= 2
    return None


def _fetch(source: SourceConfig) -> tuple[SourceConfig, list[str]]:
    """Завантажує домени з URL, повертаючи порожній список у разі помилки."""

    text = _read_source(source.url)
    if text is None:
        return source, []
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
    return source, domains


def update(
    *,
    dest: Path = DOMAINS_FILE,
    chunk_size: int = CHUNK_SIZE,
    sources: Iterable[str | SourceConfig] | None = None,
    config_path: Path = CONFIG_FILE,
    report_path: Path = REPORT_FILE,
    status_path: Path = STATUS_FILE,
) -> None:
    """Оновлює файл доменів, додаючи нові записи з перевірених джерел."""
    if sources is None:
        source_list = [src for src in _load_sources(config_path) if src.enabled]
    else:
        source_list = []
        for item in sources:
            if isinstance(item, SourceConfig):
                source_list.append(item)
            else:
                url = str(item)
                source_list.append(SourceConfig(name=url, url=url))
    if not source_list:
        return

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
    domain_sources: dict[str, list[SourceConfig]] = {}
    max_workers = max(1, min(MAX_PARALLEL_FETCHES, len(source_list)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for source, domains in pool.map(_fetch, source_list):
            for domain in domains:
                fetched.add(domain)
                holders = domain_sources.setdefault(domain, [])
                if source not in holders:
                    holders.append(source)

    new_candidates = fetched - existing
    scored = sorted(
        new_candidates,
        key=lambda item: (
            -max((src.weight for src in domain_sources.get(item, [])), default=0.0),
            item,
        ),
    )
    new_domains = scored[:chunk_size]
    if new_domains:
        needs_rewrite = True
    if not new_domains and not needs_rewrite:
        return

    merged = sorted(existing | set(new_domains))
    dest.write_text("\n".join(merged) + "\n")

    _write_report(
        report_path,
        added=new_domains,
        total=len(merged),
        sources=[src.name for src in source_list],
        stale_candidates=sorted(existing - fetched)[:50],
    )
    _update_status(
        status_path,
        merged,
        domain_sources,
    )


def _write_report(
    report_path: Path,
    *,
    added: Sequence[str],
    total: int,
    sources: Sequence[str],
    stale_candidates: Sequence[str],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at": timestamp,
        "added": list(added),
        "total_after_update": total,
        "sources": list(sources),
    }
    if stale_candidates:
        payload["stale_candidates"] = list(stale_candidates)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _update_status(
    status_path: Path,
    merged: Sequence[str],
    domain_sources: dict[str, list[SourceConfig]],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    if status_path.exists():
        raw = json.loads(status_path.read_text() or "{}")
    else:
        raw = {}

    status_data: dict[str, dict[str, object]] = {str(k): dict(v) for k, v in raw.items()}

    merged_set = set(merged)
    for domain in merged:
        info = status_data.get(domain, {})
        info.setdefault("first_seen", timestamp)
        if domain in domain_sources:
            info["last_seen"] = timestamp
            info["status"] = "active"
            info["sources"] = sorted({src.name for src in domain_sources[domain]})
        else:
            info.setdefault("last_seen", info["first_seen"])
            info["status"] = "stale"
        status_data[domain] = info

    for domain in list(status_data.keys()):
        if domain not in merged_set:
            info = status_data[domain]
            info["status"] = "removed"
            info["removed_at"] = timestamp
            status_data[domain] = info

    status_path.write_text(json.dumps(status_data, ensure_ascii=False, indent=2) + "\n")


def main(argv: list[str] | None = None) -> None:
    """CLI-обгортка для оновлення списку доменів."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--dest", type=Path, default=DOMAINS_FILE)
    parser.add_argument("--config", type=Path, default=CONFIG_FILE)
    parser.add_argument("--report", type=Path, default=REPORT_FILE)
    parser.add_argument("--status", type=Path, default=STATUS_FILE)
    args = parser.parse_args(argv)
    update(
        dest=args.dest,
        chunk_size=args.chunk_size,
        config_path=args.config,
        report_path=args.report,
        status_path=args.status,
    )


if __name__ == "__main__":
    main()
