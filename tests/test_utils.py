import json

from scripts.utils import (
    FalsePositiveRecord,
    load_catalog,
    load_entries,
    load_false_positive_lists,
    load_false_positive_records,
)


def test_load_entries(tmp_path):
    file = tmp_path / "list.txt"
    file.write_text("a.com\n# коментар\n\nB.COM\n")
    assert load_entries(file) == ["a.com", "b.com"]


def test_load_catalog_and_iter(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "domains": [
                    {
                        "value": "example.com",
                        "category": "фішинг",
                        "regions": ["global"],
                        "sources": ["тест"],
                        "status": "active",
                    }
                ],
                "regexes": [],
            },
            ensure_ascii=False,
        )
    )
    catalog = load_catalog(catalog_file)
    values = list(
        catalog.iter_values_from(
            ["example.com", "other.com"],
            kind="domain",
            categories=["фішинг"],
            regions=None,
            sources=None,
            statuses=["active"],
        )
    )
    assert values == [("example.com", catalog.metadata_for("example.com", "domain"))]


def test_load_false_positive_lists(tmp_path):
    data_file = tmp_path / "false.json"
    data_file.write_text(
        json.dumps(
            {
                "domains": ["Example.com", {"value": "Trusted.org"}],
                "regexes": ["bad", {"value": "^allow\\.ru$"}],
            }
        )
    )
    domains, regexes = load_false_positive_lists(data_file)
    assert domains == {"example.com", "trusted.org"}
    assert regexes == {"bad", "^allow\\.ru$"}


def test_load_false_positive_records(tmp_path):
    data_file = tmp_path / "false.json"
    data_file.write_text(
        json.dumps(
            {
                "domains": [
                    {
                        "value": "Good.example",
                        "reason": "Легітимний сервіс",
                        "reported_by": "user@example.com",
                        "reported_at": "2025-01-10",
                        "review_status": "confirmed",
                        "action": "exclude",
                        "notes": "Перевірено модератором",
                        "evidence": ["https://status.example.com"],
                    }
                ],
                "regexes": [
                    {
                        "value": "^safe\\.example$",
                        "reason": "Збіги з легітимними піддоменами",
                        "action": "monitor",
                    }
                ],
            },
            ensure_ascii=False,
        )
    )

    domain_records, regex_records = load_false_positive_records(data_file)

    assert domain_records == [
        FalsePositiveRecord(
            value="good.example",
            original_value="Good.example",
            reason="Легітимний сервіс",
            reported_by="user@example.com",
            reported_at="2025-01-10",
            review_status="confirmed",
            action="exclude",
            notes="Перевірено модератором",
            evidence=("https://status.example.com",),
        )
    ]
    assert regex_records == [
        FalsePositiveRecord(
            value="^safe\\.example$",
            original_value="^safe\\.example$",
            reason="Збіги з легітимними піддоменами",
            action="monitor",
        )
    ]


def test_iter_values_filters_severity_and_tags(tmp_path):
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text(
        json.dumps(
            {
                "domains": [
                    {
                        "value": "phish.example",
                        "category": "фішинг",
                        "regions": ["global"],
                        "sources": ["тест"],
                        "status": "active",
                        "severity": "високий",
                        "tags": ["цільовий", "фішинг"],
                    },
                    {
                        "value": "benign.example",
                        "category": "інше",
                        "regions": ["global"],
                        "sources": ["тест"],
                        "status": "active",
                        "severity": "низький",
                        "tags": ["whitelist"],
                    },
                ],
                "regexes": [],
            },
            ensure_ascii=False,
        )
    )

    catalog = load_catalog(catalog_file)
    values = list(
        catalog.iter_values_from(
            ["phish.example", "benign.example", "unknown.example"],
            kind="domain",
            severities=["високий"],
            tags=["фішинг"],
        )
    )

    assert values == [("phish.example", catalog.metadata_for("phish.example", "domain"))]
