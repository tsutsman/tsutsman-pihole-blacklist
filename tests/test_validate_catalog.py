import json
from pathlib import Path

import pytest

from scripts import validate_catalog


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_validate_catalog_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    catalog_path = tmp_path / "catalog.json"
    policy_path = tmp_path / "policy.json"
    _write_json(
        catalog_path,
        {
            "domains": [
                {
                    "value": "example.com",
                    "category": "пропаганда",
                    "regions": ["ru"],
                    "sources": ["ручне внесення"],
                    "severity": "висока",
                    "status": "active",
                    "added": "2024-01-10",
                    "notes": "",
                }
            ],
            "regexes": [
                {
                    "value": "(^|\\.)ru$",
                    "category": "державні-зони",
                    "regions": ["ru"],
                    "sources": ["ручне внесення"],
                    "severity": "висока",
                    "status": "active",
                    "added": "2024-01-10",
                    "notes": "",
                }
            ],
        },
    )
    _write_json(
        policy_path,
        {
            "domains": {
                "required_fields": ["value", "category", "regions", "sources", "severity", "status", "added"],
                "allowed_categories": ["пропаганда"],
                "allowed_regions": ["ru"],
                "allowed_statuses": ["active"],
                "allowed_severities": ["висока"],
                "min_sources": 1,
            },
            "regexes": {
                "required_fields": ["value", "category", "regions", "sources", "severity", "status", "added"],
                "allowed_categories": ["державні-зони"],
                "allowed_regions": ["ru"],
                "allowed_statuses": ["active"],
                "allowed_severities": ["висока"],
                "min_sources": 1,
            },
        },
    )

    exit_code = validate_catalog.main([
        "--catalog",
        str(catalog_path),
        "--policy",
        str(policy_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Каталог відповідає" in captured.out


def test_validate_catalog_reports_missing_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog_path = tmp_path / "catalog.json"
    policy_path = tmp_path / "policy.json"
    _write_json(
        catalog_path,
        {
            "domains": [
                {
                    "value": "example.com",
                    "category": "пропаганда",
                    "regions": ["ru"],
                    "sources": [],
                    "status": "inactive",
                    "added": "2024-01-10",
                }
            ],
            "regexes": [],
        },
    )
    _write_json(
        policy_path,
        {
            "domains": {
                "required_fields": ["value", "category", "regions", "sources", "severity", "status", "added"],
                "allowed_categories": ["пропаганда"],
                "allowed_regions": ["ru"],
                "allowed_statuses": ["active", "inactive"],
                "allowed_severities": ["висока"],
                "min_sources": 1,
                "require_notes_for": {"status": ["inactive"]},
            }
        },
    )

    exit_code = validate_catalog.main([
        "--catalog",
        str(catalog_path),
        "--policy",
        str(policy_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "відсутнє обов'язкове поле 'severity'" in captured.out
    assert "джерел недостатньо" in captured.out
    assert "необхідно заповнити поле 'notes'" in captured.out
