from __future__ import annotations

import json
from pathlib import Path

from scripts import generate_dashboard


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_build_dashboard_aggregates_metrics(tmp_path) -> None:
    domains_path = tmp_path / "domains.txt"
    regex_path = tmp_path / "regex.list"
    catalog_path = tmp_path / "catalog.json"
    fp_path = tmp_path / "false.json"
    latest_update_path = tmp_path / "latest.json"

    _write(domains_path, "alpha.example\nbeta.example\n")
    _write(regex_path, "^r\\.example$\nunknown\n")

    catalog_data = {
        "domains": [
            {
                "value": "alpha.example",
                "category": "пропаганда",
                "regions": ["eu"],
                "sources": ["Source A"],
                "status": "active",
                "severity": "висока",
                "monitor": True,
                "tags": ["tag-a"],
            }
        ],
        "regexes": [
            {
                "value": "^r\\.example$",
                "category": "фішинг",
                "regions": ["global"],
                "sources": ["Source B"],
                "status": "active",
                "severity": "середня",
                "tags": ["tag-r"],
            }
        ],
    }
    _write(catalog_path, json.dumps(catalog_data))

    fp_data = {
        "domains": [
            {
                "value": "alpha.example",
                "review_status": "confirmed",
                "action": "exclude",
            }
        ],
        "regexes": [
            {
                "value": "^r\\.example$",
                "review_status": "under-review",
            }
        ],
    }
    _write(fp_path, json.dumps(fp_data))

    latest_data = {
        "generated_at": "2025-02-01T00:00:00Z",
        "total_after_update": 2,
        "added": ["alpha.example"],
        "stale_candidates": ["old.example"],
        "source_health": {"Source A": "ok"},
    }
    _write(latest_update_path, json.dumps(latest_data))

    snapshot = generate_dashboard.build_dashboard(
        domains_path=domains_path,
        regex_path=regex_path,
        catalog_path=catalog_path,
        false_positive_path=fp_path,
        latest_update_path=latest_update_path,
    )

    assert snapshot["totals"] == {"domains": 2, "regexes": 2}
    assert snapshot["metadata"]["domains"]["with_metadata"] == 1
    assert snapshot["metadata"]["regexes"]["with_metadata"] == 1
    assert snapshot["monitored"]["domains"] == 1
    assert snapshot["domains"]["categories"] == {"пропаганда": 1}
    assert snapshot["regexes"]["categories"] == {"фішинг": 1}
    assert snapshot["false_positives"]["domains"]["by_status"] == {"confirmed": 1}
    assert snapshot["false_positives"]["regexes"]["by_status"] == {"under-review": 1}
    assert snapshot["latest_update"]["added_count"] == 1
    assert snapshot["latest_update"]["stale_candidates_count"] == 1


def test_update_history_appends_and_trims(tmp_path) -> None:
    history_path = tmp_path / "history.json"
    snapshot = {
        "generated_at": "2025-02-01T00:00:00+00:00",
        "totals": {"domains": 10, "regexes": 2},
        "metadata": {
            "domains": {"with_metadata": 8, "without_metadata": 2},
            "regexes": {"with_metadata": 2, "without_metadata": 0},
        },
        "monitored": {"domains": 3},
    }

    history = generate_dashboard.update_history(history_path, snapshot, limit=2)
    assert len(history) == 1

    snapshot_next = {
        "generated_at": "2025-02-02T00:00:00+00:00",
        "totals": {"domains": 11, "regexes": 2},
        "metadata": {
            "domains": {"with_metadata": 9, "without_metadata": 2},
            "regexes": {"with_metadata": 2, "without_metadata": 0},
        },
        "monitored": {"domains": 4},
    }

    generate_dashboard.update_history(history_path, snapshot_next, limit=2)
    history_data = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(history_data) == 2
    assert history_data[0]["generated_at"] == "2025-02-01T00:00:00+00:00"

    snapshot_third = {
        "generated_at": "2025-02-03T00:00:00+00:00",
        "totals": {"domains": 12, "regexes": 3},
        "metadata": {
            "domains": {"with_metadata": 10, "without_metadata": 2},
            "regexes": {"with_metadata": 3, "without_metadata": 0},
        },
        "monitored": {"domains": 5},
    }

    trimmed = generate_dashboard.update_history(history_path, snapshot_third, limit=2)
    assert len(trimmed) == 2
    assert trimmed[0]["generated_at"] == "2025-02-02T00:00:00+00:00"
