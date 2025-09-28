import json

import scripts.audit_lists as audit_lists


def _prepare(
    tmp_path,
    monkeypatch,
    *,
    domains: str = "alpha.com\nbeta.com\nalpha.com\n",
    regex: str = "bad.*\n",
    catalog: dict | None = None,
):
    domains_path = tmp_path / "domains.txt"
    regex_path = tmp_path / "regex.list"
    catalog_path = tmp_path / "catalog.json"
    domains_path.write_text(domains, encoding="utf-8")
    regex_path.write_text(regex, encoding="utf-8")
    catalog_path.write_text(
        json.dumps(
            catalog
            or {
                "version": 3,
                "domains": [
                    {"value": "alpha.com", "status": "active"},
                ],
                "regexes": [
                    {"value": "bad.*", "status": "active"},
                    {"value": "unused.*", "status": "inactive"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit_lists, "DOMAINS_FILE", domains_path)
    monkeypatch.setattr(audit_lists, "REGEX_FILE", regex_path)
    monkeypatch.setattr(audit_lists, "CATALOG_FILE", catalog_path)
    return domains_path, regex_path, catalog_path


def test_build_audit_collects_statistics(tmp_path, monkeypatch):
    _prepare(tmp_path, monkeypatch)
    domains = audit_lists.load_entries(audit_lists.DOMAINS_FILE)
    regexes = audit_lists.load_entries(audit_lists.REGEX_FILE)
    catalog = audit_lists.load_catalog(audit_lists.CATALOG_FILE)

    summary = audit_lists.build_audit(domains, regexes, catalog, version=3)

    domain_summary = summary["domains"]
    assert domain_summary["total"] == 3
    assert domain_summary["duplicates"] == ["alpha.com"]
    assert domain_summary["missing_metadata"] == ["beta.com"]
    assert domain_summary["status_breakdown"] == {"active": 1}
    assert domain_summary["coverage"] == 0.5

    regex_summary = summary["regexes"]
    assert regex_summary["total"] == 1
    assert regex_summary["coverage"] == 1.0

    catalog_summary = summary["catalog"]
    assert catalog_summary["version"] == 3
    assert catalog_summary["orphan_regexes"] == ["unused.*"]


def test_main_writes_output(tmp_path, monkeypatch, capsys):
    _, _, catalog_path = _prepare(tmp_path, monkeypatch)
    output_path = tmp_path / "audit.json"

    code = audit_lists.main(["--output", str(output_path)])
    assert code == 0

    stdout = capsys.readouterr().out
    data = json.loads(stdout)
    assert data["catalog"]["version"] == 3

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["catalog"]["version"] == 3


def test_allows_custom_paths(tmp_path, monkeypatch):
    domains_path, regex_path, catalog_path = _prepare(tmp_path, monkeypatch)
    other_domains = tmp_path / "domains2.txt"
    other_domains.write_text("gamma.com\n", encoding="utf-8")

    code = audit_lists.main(
        [
            "--domains",
            str(other_domains),
            "--regex",
            str(regex_path),
            "--catalog",
            str(catalog_path),
        ]
    )

    assert code == 0
