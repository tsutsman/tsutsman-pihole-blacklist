"""Завантажує домени з перевірених джерел і оновлює domains.txt."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from http.client import IncompleteRead
import time
from pathlib import Path
from typing import Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import urlopen

CHUNK_SIZE = 500
MAX_PARALLEL_FETCHES = 4
MAX_RETRIES = 3
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

DOMAINS_FILE = Path("domains.txt")
CONFIG_FILE = Path("data/sources.json")
REPORT_FILE = Path("reports/latest_update.json")
REPORT_MARKDOWN_FILE = Path("reports/latest_update.md")
STATUS_FILE = Path("data/domain_status.json")
SOURCE_CACHE_FILE = Path("data/source_cache.json")
PREVIEW_LIMIT = 20
_HOST_PREFIXES: tuple[str, ...] = (
    "0.0.0.0",
    "127.0.0.1",
    "255.255.255.255",
    "::",
    "::1",
)


def _record_example(collection: list, item, *, unique: bool = False) -> None:
    """Додає приклад до списку з обмеженням кількості та унікальністю."""

    if unique and item in collection:
        return
    if len(collection) < PREVIEW_LIMIT:
        collection.append(item)


def _unique_preserve_order(values: Iterable[str]) -> list[str]:
    """Повертає список без дублікатів, зберігаючи початковий порядок."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


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


def _load_source_cache(path: Path) -> dict[str, dict[str, object]]:
    """Завантажує локальний кеш джерел із відновленням після пошкодження."""

    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text() or "{}")
    except json.JSONDecodeError:
        return {}
    cache: dict[str, dict[str, object]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        domains = value.get("domains")
        if not isinstance(domains, list):
            continue
        cache[key] = {
            "domains": [str(item) for item in domains if isinstance(item, str)],
            "fetched_at": value.get("fetched_at"),
        }
    return cache


def _store_source_cache(path: Path, data: dict[str, dict[str, object]]) -> None:
    """Зберігає кеш джерел у JSON із безпечним створенням директорій."""

    payload: dict[str, dict[str, object]] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        domains = value.get("domains")
        if not isinstance(domains, list):
            continue
        fetched_at = value.get("fetched_at")
        payload[key] = {
            "domains": _unique_preserve_order(domains),
            "fetched_at": fetched_at,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _cache_is_fresh(source: SourceConfig, fetched_at: object, *, now: datetime) -> bool:
    """Перевіряє, чи ще актуальний кеш для джерела."""

    if not isinstance(fetched_at, str):
        return False
    try:
        timestamp = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    interval_days = max(1, int(source.update_interval_days))
    ttl = timedelta(days=interval_days)
    return timestamp + ttl > now


def update(
    *,
    dest: Path = DOMAINS_FILE,
    chunk_size: int = CHUNK_SIZE,
    sources: Iterable[str | SourceConfig] | None = None,
    config_path: Path = CONFIG_FILE,
    report_path: Path = REPORT_FILE,
    markdown_path: Path = REPORT_MARKDOWN_FILE,
    status_path: Path = STATUS_FILE,
    cache_path: Path = SOURCE_CACHE_FILE,
) -> None:
    """Оновлює файл доменів, додаючи нові записи з перевірених джерел.

    Кешування вмісту джерел дозволяє уникати повторного завантаження
    списків, якщо з моменту попереднього звернення не минув інтервал,
    заданий у конфігурації.
    """
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
    normalized_total = 0
    normalized_preview: list[tuple[str, str]] = []
    duplicate_count = 0
    duplicate_preview: list[str] = []
    duplicate_domains: set[str] = set()
    invalid_total = 0
    invalid_preview: list[str] = []
    if dest.exists():
        for line in dest.read_text().splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            domain = _clean_domain(stripped)
            if domain:
                if domain != stripped:
                    normalized_total += 1
                    _record_example(normalized_preview, (stripped, domain), unique=True)
                    needs_rewrite = True
                if domain in existing:
                    duplicate_count += 1
                    duplicate_domains.add(domain)
                    _record_example(duplicate_preview, domain, unique=True)
                    needs_rewrite = True
                else:
                    existing.add(domain)
            else:
                invalid_total += 1
                _record_example(invalid_preview, stripped, unique=True)
                needs_rewrite = True

    fetched: set[str] = set()
    domain_sources: dict[str, list[SourceConfig]] = {}
    cache = _load_source_cache(cache_path)
    now = datetime.now(timezone.utc)
    pending_fetch: list[SourceConfig] = []
    cached_results: dict[SourceConfig, list[str]] = {}

    for source in source_list:
        cached = cache.get(source.url)
        if cached and _cache_is_fresh(source, cached.get("fetched_at"), now=now):
            domains = _unique_preserve_order(
                d for d in cached.get("domains", []) if isinstance(d, str)
            )
            cached_results[source] = domains
            continue
        pending_fetch.append(source)

    if pending_fetch:
        max_workers = max(1, min(MAX_PARALLEL_FETCHES, len(pending_fetch)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for source, domains in pool.map(_fetch, pending_fetch):
                deduplicated = _unique_preserve_order(domains)
                if deduplicated:
                    cached_results[source] = deduplicated
                    cache[source.url] = {
                        "domains": deduplicated,
                        "fetched_at": now.isoformat(),
                    }
                else:
                    cache[source.url] = {
                        "domains": [],
                        "fetched_at": now.isoformat(),
                    }

    for source, domains in cached_results.items():
        for domain in domains:
            fetched.add(domain)
            holders = domain_sources.setdefault(domain, [])
            if source not in holders:
                holders.append(source)

    _store_source_cache(cache_path, cache)

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

    normalized_info = {
        "total": normalized_total,
        "preview": [
            {"original": original, "normalized": normalized}
            for original, normalized in sorted(normalized_preview, key=lambda item: item[1])
        ],
    }
    duplicates_info = {
        "total": duplicate_count,
        "unique": len(duplicate_domains),
        "preview": sorted(duplicate_preview),
    }
    invalid_info = {
        "total": invalid_total,
        "preview": sorted(invalid_preview),
    }

    report_payload = _write_report(
        report_path,
        added=new_domains,
        total=len(merged),
        sources=[src.name for src in source_list],
        stale_candidates=sorted(existing - fetched)[:50],
        normalized=normalized_info,
        duplicates=duplicates_info,
        invalid=invalid_info,
    )
    _write_markdown_report(markdown_path, report_payload)
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
    normalized: dict[str, object],
    duplicates: dict[str, object],
    invalid: dict[str, object],
) -> dict[str, object]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    payload: dict[str, object] = {
        "generated_at": timestamp,
        "added": list(added),
        "total_after_update": total,
        "sources": list(sources),
        "normalized": normalized,
        "duplicates_removed": duplicates,
        "invalid_lines": invalid,
    }
    if stale_candidates:
        payload["stale_candidates"] = list(stale_candidates)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def _write_markdown_report(path: Path, data: dict[str, object]) -> None:
    """Створює людиночитний Markdown-звіт за результатами оновлення."""

    path.parent.mkdir(parents=True, exist_ok=True)
    added = list(data.get("added", []))
    normalized_info = data.get("normalized")
    if not isinstance(normalized_info, dict):
        normalized_info = {"total": 0, "preview": []}
    duplicates_info = data.get("duplicates_removed")
    if not isinstance(duplicates_info, dict):
        duplicates_info = {"total": 0, "preview": [], "unique": 0}
    invalid_info = data.get("invalid_lines")
    if not isinstance(invalid_info, dict):
        invalid_info = {"total": 0, "preview": []}
    stale = list(data.get("stale_candidates", []))

    def _calc_rest(total: int, preview: Sequence[object]) -> int:
        return max(0, total - len(preview))

    lines = [
        "# Звіт про оновлення доменів",
        "",
        f"- Згенеровано: {data.get('generated_at', 'невідомо')}",
        f"- Додано нових доменів: {len(added)}",
        f"- Загальна кількість доменів: {data.get('total_after_update', 'невідомо')}",
        f"- Нормалізовано записів: {normalized_info.get('total', 0)}",
        f"- Видалено дублікати: {duplicates_info.get('total', 0)}",
        f"- Унікальних дублікатів: {duplicates_info.get('unique', 0)}",
        f"- Пропущено некоректних рядків: {invalid_info.get('total', 0)}",
        f"- Потенційно застарілих кандидатів: {len(stale)}",
    ]

    if added:
        lines.extend(["", "## Нові домени (перші приклади)", ""])
        preview = added[:PREVIEW_LIMIT]
        lines.extend(f"- {item}" for item in preview)
        rest = _calc_rest(len(added), preview)
        if rest:
            lines.append(f"... ще {rest} доменів")

    normalized_preview = normalized_info.get("preview", [])
    if normalized_preview:
        lines.extend(["", "## Нормалізовані записи", ""])
        for entry in normalized_preview[:PREVIEW_LIMIT]:
            original = entry.get("original") if isinstance(entry, dict) else None
            normalized_value = entry.get("normalized") if isinstance(entry, dict) else None
            if original is None or normalized_value is None:
                continue
            lines.append(f"- {normalized_value} ← `{original}`")
        rest = _calc_rest(normalized_info.get("total", 0), normalized_preview)
        if rest:
            lines.append(f"... ще {rest} записів")

    duplicate_preview = duplicates_info.get("preview", [])
    if duplicate_preview:
        lines.extend(["", "## Дублікати", ""])
        preview_items = list(duplicate_preview)[:PREVIEW_LIMIT]
        lines.extend(f"- {item}" for item in preview_items)
        rest = _calc_rest(duplicates_info.get("unique", 0), preview_items)
        if rest:
            lines.append(f"... ще {rest} дублікатів")

    invalid_preview = invalid_info.get("preview", [])
    if invalid_preview:
        lines.extend(["", "## Некоректні рядки", ""])
        preview_items = list(invalid_preview)[:PREVIEW_LIMIT]
        lines.extend(f"- `{item}`" for item in preview_items)
        rest = _calc_rest(invalid_info.get("total", 0), preview_items)
        if rest:
            lines.append(f"... ще {rest} рядків")

    if stale:
        lines.extend(["", "## Потенційно застарілі домени", ""])
        preview_items = stale[:PREVIEW_LIMIT]
        lines.extend(f"- {item}" for item in preview_items)
        rest = _calc_rest(len(stale), preview_items)
        if rest:
            lines.append(f"... ще {rest} доменів")

    content = "\n".join(lines).rstrip() + "\n"
    path.write_text(content)


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
    parser.add_argument("--markdown-report", type=Path, default=REPORT_MARKDOWN_FILE)
    parser.add_argument("--status", type=Path, default=STATUS_FILE)
    args = parser.parse_args(argv)
    update(
        dest=args.dest,
        chunk_size=args.chunk_size,
        config_path=args.config,
        report_path=args.report,
        markdown_path=args.markdown_report,
        status_path=args.status,
    )


if __name__ == "__main__":
    main()
