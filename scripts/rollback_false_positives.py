#!/usr/bin/env python3
"""Автоматизація відкату для підтверджених хибнопозитивів."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from scripts.utils import FalsePositiveRecord, load_entries, load_false_positive_records

DOMAINS_FILE = Path("domains.txt")
REGEX_FILE = Path("regex.list")
FALSE_POSITIVES_FILE = Path("data/false_positives.json")
DEFAULT_OUTPUT_DIR = Path("dist/rollback")
EXCLUDE_ACTIONS = {"exclude", "remove"}


def _write_list(path: Path, entries: Iterable[str]) -> None:
    """Записує перелік у файл із кінцевим перенесенням рядка."""

    lines = list(entries)
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _split_records(
    records: list[FalsePositiveRecord],
    present_values: set[str],
) -> tuple[list[FalsePositiveRecord], list[FalsePositiveRecord], list[FalsePositiveRecord]]:
    """Розділяє записи на вилучені, відсутні та ті, що залишаються."""

    excluded: list[FalsePositiveRecord] = []
    missing: list[FalsePositiveRecord] = []
    retained: list[FalsePositiveRecord] = []

    for record in records:
        action = (record.action or "").lower()
        if action in EXCLUDE_ACTIONS:
            if record.value in present_values:
                excluded.append(record)
            else:
                missing.append(record)
        else:
            retained.append(record)
    return excluded, missing, retained


def _build_summary(
    *,
    domains_initial: list[str],
    regex_initial: list[str],
    domains_filtered: list[str],
    regex_filtered: list[str],
    excluded_domains: list[FalsePositiveRecord],
    excluded_regexes: list[FalsePositiveRecord],
    missing_domains: list[FalsePositiveRecord],
    missing_regexes: list[FalsePositiveRecord],
    retained_domains: list[FalsePositiveRecord],
    retained_regexes: list[FalsePositiveRecord],
    false_positive_file: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Формує JSON-звіт про виконаний відкат."""

    summary = {
        "source": str(false_positive_file),
        "generated": {
            "domains": str(output_dir / "domains.txt"),
            "regexes": str(output_dir / "regex.list"),
        },
        "stats": {
            "initial_domains": len(domains_initial),
            "filtered_domains": len(domains_filtered),
            "initial_regexes": len(regex_initial),
            "filtered_regexes": len(regex_filtered),
        },
        "excluded": {
            "domains": [record.as_dict() for record in excluded_domains],
            "regexes": [record.as_dict() for record in excluded_regexes],
        },
        "missing": {
            "domains": [record.as_dict() for record in missing_domains],
            "regexes": [record.as_dict() for record in missing_regexes],
        },
        "retained": {
            "domains": [record.as_dict() for record in retained_domains],
            "regexes": [record.as_dict() for record in retained_regexes],
        },
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    """Точка входу для CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domains", type=Path, default=DOMAINS_FILE)
    parser.add_argument("--regexes", type=Path, default=REGEX_FILE)
    parser.add_argument("--false-positives", type=Path, default=FALSE_POSITIVES_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    try:
        domains = load_entries(args.domains)
    except FileNotFoundError:
        print(f"Не знайдено файл зі списком доменів: {args.domains}")
        return 2

    try:
        regexes = load_entries(args.regexes)
    except FileNotFoundError:
        print(f"Не знайдено файл регулярних виразів: {args.regexes}")
        return 2

    domain_records, regex_records = load_false_positive_records(args.false_positives)

    domain_set = set(domains)
    regex_set = set(regexes)

    excluded_domains, missing_domains, retained_domains = _split_records(
        domain_records,
        domain_set,
    )
    excluded_regexes, missing_regexes, retained_regexes = _split_records(
        regex_records,
        regex_set,
    )

    excluded_domain_values = {record.value for record in excluded_domains}
    excluded_regex_values = {record.value for record in excluded_regexes}

    filtered_domains = [value for value in domains if value not in excluded_domain_values]
    filtered_regexes = [value for value in regexes if value not in excluded_regex_values]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    domains_path = args.output_dir / "domains.txt"
    regex_path = args.output_dir / "regex.list"
    _write_list(domains_path, filtered_domains)
    _write_list(regex_path, filtered_regexes)

    summary = _build_summary(
        domains_initial=domains,
        regex_initial=regexes,
        domains_filtered=filtered_domains,
        regex_filtered=filtered_regexes,
        excluded_domains=excluded_domains,
        excluded_regexes=excluded_regexes,
        missing_domains=missing_domains,
        missing_regexes=missing_regexes,
        retained_domains=retained_domains,
        retained_regexes=retained_regexes,
        false_positive_file=args.false_positives,
        output_dir=args.output_dir,
    )

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
