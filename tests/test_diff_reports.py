from __future__ import annotations

import json

import pytest

from scripts import diff_reports


def test_build_diff_detects_changes() -> None:
    previous = {
        "generated_at": "2025-01-01T00:00:00Z",
        "added": ["alpha.example", "beta.example"],
        "stale_candidates": ["old.example"],
        "sources": ["Source A"],
        "total_after_update": 100,
    }
    current = {
        "generated_at": "2025-01-02T00:00:00Z",
        "added": ["beta.example", "gamma.example"],
        "stale_candidates": ["old.example", "new-stale.example"],
        "sources": ["Source A", "Source B"],
        "total_after_update": 105,
    }

    diff = diff_reports.build_diff(previous, current)

    assert diff["previous_generated_at"] == "2025-01-01T00:00:00Z"
    assert diff["current_generated_at"] == "2025-01-02T00:00:00Z"
    assert diff["delta_total"] == 5
    assert diff["added_since_previous"] == ["gamma.example"]
    assert diff["removed_from_added"] == ["alpha.example"]
    assert diff["new_stale_candidates"] == ["new-stale.example"]
    assert diff["resolved_stale_candidates"] == []
    assert diff["new_sources"] == ["Source B"]
    assert diff["removed_sources"] == []


def test_build_diff_validates_collection_types() -> None:
    previous = {"added": "not-a-list", "total_after_update": 0}
    current = {"total_after_update": 0}

    with pytest.raises(TypeError):
        diff_reports.build_diff(previous, current)


def test_main_prints_and_writes_diff(tmp_path, capsys) -> None:
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"
    output_path = tmp_path / "diff.json"
    history_path = tmp_path / "history.json"

    previous_path.write_text(
        json.dumps({
            "generated_at": "2025-01-01T00:00:00Z",
            "added": ["alpha.example"],
            "total_after_update": 10,
        }),
        encoding="utf-8",
    )
    current_path.write_text(
        json.dumps({
            "generated_at": "2025-01-02T00:00:00Z",
            "added": ["alpha.example", "beta.example"],
            "total_after_update": 12,
        }),
        encoding="utf-8",
    )

    exit_code = diff_reports.main(
        [
            str(previous_path),
            str(current_path),
            "--output",
            str(output_path),
            "--history",
            str(history_path),
            "--history-limit",
            "2",
        ]
    )

    assert exit_code == 0

    stdout = capsys.readouterr().out
    printed = json.loads(stdout)
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert printed == saved
    assert printed["added_since_previous"] == ["beta.example"]
    assert printed["delta_total"] == 2
    history_data = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(history_data) == 1
    assert history_data[0]["delta_total"] == 2


def test_update_history_truncates_records(tmp_path) -> None:
    history_path = tmp_path / "history.json"
    diff = {
        "previous_generated_at": "2025-01-01T00:00:00Z",
        "current_generated_at": "2025-01-02T00:00:00Z",
        "delta_total": 1,
    }

    diff_reports.update_history(history_path, diff, limit=2)
    diff_reports.update_history(history_path, diff, limit=2)
    diff_reports.update_history(history_path, diff, limit=2)

    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert len(history) == 2
