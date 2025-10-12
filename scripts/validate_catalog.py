#!/usr/bin/env python3
"""Перевірка дотримання критеріїв включення для каталогу метаданих.

Validate that the metadata catalog follows the inclusion policy rules.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CATALOG_FILE = Path("data/catalog.json")
POLICY_FILE = Path("data/inclusion_policy.json")


class PolicyError(RuntimeError):
    """Виняток для ситуацій, коли політика описана некоректно.

    Exception raised when the inclusion policy is malformed.
    """


def load_policy(path: Path) -> dict[str, Any]:
    """Завантажує файл політик та повертає словник з правилами.

    Load the policy JSON file and return it as a dictionary.
    """

    if not path.exists():
        raise FileNotFoundError(f"Файл політик не знайдено: {path}")
    data = json.loads(path.read_text(encoding="utf-8") or "{}")
    if not isinstance(data, dict):
        raise PolicyError("Політика має бути описана у форматі JSON-словника")
    return data


def _is_empty(value: Any) -> bool:
    """Перевіряє, чи слід вважати значення порожнім.

    Determine whether a value should be treated as empty.
    """

    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return not value
    return False


def _validate_iso_date(value: str) -> bool:
    """Повертає True, якщо значення є коректною датою ISO.

    Return True when the provided value is a valid ISO-formatted date.
    """

    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_entries(entries: list[dict[str, Any]], policy: dict[str, Any], *, kind: str) -> list[str]:
    """Перевіряє перелік записів каталогу за заданими правилами.

    Validate catalog entries against policy constraints for a given kind.
    """

    errors: list[str] = []
    required_fields = list(policy.get("required_fields", []))
    allowed_categories = set(policy.get("allowed_categories", []))
    allowed_regions = set(policy.get("allowed_regions", []))
    allowed_statuses = set(policy.get("allowed_statuses", []))
    allowed_severities = set(policy.get("allowed_severities", []))
    min_sources = int(policy.get("min_sources", 0))
    require_notes_for = policy.get("require_notes_for", {})

    for entry in entries:
        value = str(entry.get("value", "")).strip()
        label = f"{kind} '{value or '<невідомо>'}'"

        for field in required_fields:
            if field not in entry or _is_empty(entry[field]):
                errors.append(f"{label}: відсутнє обов'язкове поле '{field}'")

        category = entry.get("category")
        if allowed_categories and category not in allowed_categories:
            errors.append(
                f"{label}: категорія '{category}' не входить до дозволеного переліку"
            )

        regions = entry.get("regions", [])
        if allowed_regions and (
            _is_empty(regions) or any(region not in allowed_regions for region in regions)
        ):
            errors.append(
                f"{label}: регіони {regions!r} виходять за межі дозволених {sorted(allowed_regions)}"
            )

        status = entry.get("status")
        if allowed_statuses and status not in allowed_statuses:
            errors.append(
                f"{label}: статус '{status}' не дозволений політикою"
            )

        severity = entry.get("severity")
        if allowed_severities and severity not in allowed_severities:
            errors.append(
                f"{label}: рівень загрози '{severity}' не відповідає політиці"
            )

        sources = entry.get("sources", [])
        if min_sources and (not isinstance(sources, list) or len(sources) < min_sources):
            errors.append(
                f"{label}: джерел недостатньо (мінімум {min_sources})"
            )

        if entry.get("added") and not _validate_iso_date(str(entry["added"])):
            errors.append(f"{label}: поле 'added' має бути датою у форматі ISO 8601")

        required_statuses = set(require_notes_for.get("status", []))
        if required_statuses and status in required_statuses:
            if _is_empty(entry.get("notes")):
                errors.append(
                    f"{label}: для статусу '{status}' необхідно заповнити поле 'notes'"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI-інтерфейс перевірки каталогу за критеріями включення.

    Command-line interface for enforcing inclusion policy compliance.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG_FILE)
    parser.add_argument("--policy", type=Path, default=POLICY_FILE)
    args = parser.parse_args(argv)

    try:
        catalog_data = json.loads(args.catalog.read_text(encoding="utf-8") or "{}")
    except FileNotFoundError:
        print(f"Каталог не знайдено: {args.catalog}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"Не вдалося розпарсити каталог {args.catalog}: {exc}")
        return 2

    try:
        policy = load_policy(args.policy)
    except (FileNotFoundError, PolicyError) as exc:
        print(str(exc))
        return 2
    except json.JSONDecodeError as exc:
        print(f"Не вдалося розпарсити політику {args.policy}: {exc}")
        return 2

    domains_errors = _validate_entries(
        list(catalog_data.get("domains", [])),
        dict(policy.get("domains", {})),
        kind="домен",
    )
    regex_errors = _validate_entries(
        list(catalog_data.get("regexes", [])),
        dict(policy.get("regexes", {})),
        kind="шаблон",
    )

    errors = domains_errors + regex_errors
    if errors:
        print("\n".join(errors))
        return 1

    print("Каталог відповідає критеріям включення")
    return 0


if __name__ == "__main__":
    sys.exit(main())
