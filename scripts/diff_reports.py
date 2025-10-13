"""Порівняння JSON-звітів оновлень для історичного моніторингу.

Скрипт дає змогу проаналізувати два файли формату `latest_update.json`
та сформувати диференційований звіт із ключовими показниками:

* зміни у кількості доменів (`delta_total`);
* нові та видалені домени у секції `added`;
* зміни серед кандидатів на застарівання;
* появу або видалення джерел даних.

Результат повертається у форматі JSON та може бути збережений у файл
для подальшого використання в CI або при підготовці релізних нотаток.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_report(path: Path) -> dict[str, Any]:
    """Зчитує JSON-звіт та повертає словник з даними."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:  # pragma: no cover - поверхово перевіряється у main
        raise FileNotFoundError(f"Не знайдено файл звіту: {path}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - поверхово перевіряється у main
        raise ValueError(f"Некоректний JSON у файлі {path}") from exc


def _normalize_set(report: dict[str, Any], key: str) -> set[str]:
    """Повертає множину значень для вказаного ключа звіту."""

    value = report.get(key, [])
    if value is None:
        return set()
    if not isinstance(value, list):
        raise TypeError(f"Очікувався список у полі '{key}', отримано {type(value)!r}")
    return {str(item) for item in value}


def _extract_total(report: dict[str, Any]) -> int:
    total = report.get("total_after_update", 0)
    if not isinstance(total, int):
        raise TypeError(
            "Поле 'total_after_update' має бути цілим числом, отримано"
            f" {type(total)!r}"
        )
    return total


def build_diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Обчислює відмінності між двома звітами."""

    previous_added = _normalize_set(previous, "added")
    current_added = _normalize_set(current, "added")
    previous_stale = _normalize_set(previous, "stale_candidates")
    current_stale = _normalize_set(current, "stale_candidates")
    previous_sources = _normalize_set(previous, "sources")
    current_sources = _normalize_set(current, "sources")

    diff = {
        "previous_generated_at": previous.get("generated_at"),
        "current_generated_at": current.get("generated_at"),
        "delta_total": _extract_total(current) - _extract_total(previous),
        "added_since_previous": sorted(current_added - previous_added),
        "removed_from_added": sorted(previous_added - current_added),
        "new_stale_candidates": sorted(current_stale - previous_stale),
        "resolved_stale_candidates": sorted(previous_stale - current_stale),
        "new_sources": sorted(current_sources - previous_sources),
        "removed_sources": sorted(previous_sources - current_sources),
    }

    return diff


def dump_report(data: dict[str, Any]) -> str:
    """Повертає відформатоване подання звіту у вигляді JSON-рядка."""

    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Порівняння двох JSON-звітів про оновлення доменів"
    )
    parser.add_argument("previous", help="Шлях до попереднього звіту")
    parser.add_argument("current", help="Шлях до поточного звіту")
    parser.add_argument(
        "-o",
        "--output",
        help="Необов'язковий шлях для збереження диф-результату у файл",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    previous_path = Path(args.previous)
    current_path = Path(args.current)

    previous_report = _load_report(previous_path)
    current_report = _load_report(current_path)
    diff = build_diff(previous_report, current_report)

    output = dump_report(diff)
    print(output)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":  # pragma: no cover - ручний запуск
    raise SystemExit(main())
