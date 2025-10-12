import json

from scripts.rollback_false_positives import main as rollback_main


def test_rollback_creates_filtered_lists(tmp_path):
    domains_file = tmp_path / "domains.txt"
    domains_file.write_text("malicious.com\ngood.example\n", encoding="utf-8")

    regex_file = tmp_path / "regex.list"
    regex_file.write_text("^badregex$\n^keep$\n", encoding="utf-8")

    false_positive_file = tmp_path / "false.json"
    false_positive_file.write_text(
        json.dumps(
            {
                "domains": [
                    {
                        "value": "good.example",
                        "action": "exclude",
                        "reason": "Сервіс належить партнеру",
                        "review_status": "confirmed",
                    },
                    {
                        "value": "missing.example",
                        "action": "exclude",
                        "reason": "Уже вилучено з основного списку",
                    },
                ],
                "regexes": [
                    {
                        "value": "^badregex$",
                        "action": "exclude",
                        "reason": "Регулярний вираз збігається з легітимним доменом",
                    },
                    {
                        "value": "^monitor$",
                        "action": "monitor",
                        "reason": "Потребує додаткової перевірки",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "output"
    exit_code = rollback_main(
        [
            "--domains",
            str(domains_file),
            "--regexes",
            str(regex_file),
            "--false-positives",
            str(false_positive_file),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0

    filtered_domains = (output_dir / "domains.txt").read_text(encoding="utf-8").splitlines()
    filtered_regexes = (output_dir / "regex.list").read_text(encoding="utf-8").splitlines()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))

    assert filtered_domains == ["malicious.com"]
    assert filtered_regexes == ["^keep$"]

    assert summary["stats"] == {
        "initial_domains": 2,
        "filtered_domains": 1,
        "initial_regexes": 2,
        "filtered_regexes": 1,
    }
    assert summary["excluded"]["domains"][0]["value"] == "good.example"
    assert summary["missing"]["domains"][0]["value"] == "missing.example"
    assert summary["excluded"]["regexes"][0]["value"] == "^badregex$"
    assert summary["retained"]["regexes"][0]["value"] == "^monitor$"
