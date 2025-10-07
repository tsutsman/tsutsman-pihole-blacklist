import json
import socket

import scripts.check_lists as check_lists
from scripts.check_lists import (
    _find_cross_duplicates,
    _find_duplicates,
    _validate_domains,
    _validate_regexes,
)


def _prepare(tmp_path, monkeypatch, *, catalog=None, false_positives=None, domains=None, regex=None):
    domains_path = tmp_path / "domains.txt"
    regex_path = tmp_path / "regex.list"
    catalog_path = tmp_path / "catalog.json"
    fp_path = tmp_path / "false.json"
    domains_path.write_text(domains or "example.com\n")
    regex_path.write_text(regex or "good.*\n")
    catalog_path.write_text(
        json.dumps(catalog or {"domains": [], "regexes": []}, ensure_ascii=False)
    )
    fp_path.write_text(json.dumps(false_positives or {"domains": [], "regexes": []}))
    monkeypatch.setattr(check_lists, "DOMAINS_FILE", domains_path)
    monkeypatch.setattr(check_lists, "REGEX_FILE", regex_path)
    monkeypatch.setattr(check_lists, "CATALOG_FILE", catalog_path)
    monkeypatch.setattr(check_lists, "FALSE_POSITIVES_FILE", fp_path)
    return domains_path, regex_path


def test_find_duplicates():
    assert _find_duplicates(["a", "b", "a"]) == {"a"}


def test_find_duplicates_case_insensitive():
    assert _find_duplicates(["A.com", "a.com"]) == {"a.com"}


def test_find_cross_duplicates():
    assert _find_cross_duplicates(["a", "b"], ["b", "c"]) == {"b"}


def test_validate_domains():
    assert _validate_domains(["example.com", "bad_domain"]) == ["bad_domain"]


def test_validate_regexes():
    assert _validate_regexes([r"^good$", r"["]) == ["["]


def test_main_ok(tmp_path, monkeypatch, capsys):
    _prepare(tmp_path, monkeypatch)
    assert check_lists.main([]) == 0
    assert capsys.readouterr().out.strip() == "Списки коректні"


def test_main_invalid(tmp_path, monkeypatch, capsys):
    _prepare(tmp_path, monkeypatch, domains="bad_domain\n", regex="[\n")
    assert check_lists.main([]) == 1
    out = capsys.readouterr().out
    assert "Некоректні домени" in out
    assert "Некоректні регулярні вирази" in out


def test_main_detects_inactive_metadata(tmp_path, monkeypatch, capsys):
    catalog = {
        "domains": [
            {
                "value": "example.com",
                "status": "inactive",
            }
        ],
        "regexes": [],
    }
    _prepare(tmp_path, monkeypatch, catalog=catalog)
    assert check_lists.main([]) == 1
    out = capsys.readouterr().out
    assert "Домени зі статусом" in out


def test_main_requires_metadata_for_domains(tmp_path, monkeypatch, capsys):
    _prepare(
        tmp_path,
        monkeypatch,
        catalog={"domains": [], "regexes": []},
    )
    assert check_lists.main(["--require-metadata", "domains"]) == 1
    out = capsys.readouterr().out
    assert "Домени без метаданих" in out


def test_main_requires_metadata_all_success(tmp_path, monkeypatch, capsys):
    catalog = {
        "domains": [
            {
                "value": "example.com",
            }
        ],
        "regexes": [
            {
                "value": "good.*",
            }
        ],
    }
    _prepare(tmp_path, monkeypatch, catalog=catalog)
    assert check_lists.main(["--require-metadata", "all"]) == 0
    assert capsys.readouterr().out.strip() == "Списки коректні"


def test_main_reports_false_positive(tmp_path, monkeypatch, capsys):
    fp = {"domains": ["example.com"], "regexes": []}
    _prepare(tmp_path, monkeypatch, false_positives=fp)
    assert check_lists.main([]) == 1
    out = capsys.readouterr().out
    assert "Ймовірні хибнопозитивні домени" in out


def test_main_dns_check(tmp_path, monkeypatch, capsys):
    catalog = {
        "domains": [
            {
                "value": "example.com",
                "status": "active",
                "monitor": True,
            }
        ],
        "regexes": [],
    }
    _prepare(tmp_path, monkeypatch, catalog=catalog)
    calls: list[str] = []

    def fake_getaddrinfo(host, port):
        calls.append(host)
        raise socket.gaierror()

    monkeypatch.setattr(check_lists.socket, "getaddrinfo", fake_getaddrinfo)
    assert check_lists.main(["--check-dns", "--dns-sample", "1"]) == 1
    out = capsys.readouterr().out
    assert "Домени без DNS-відповіді" in out
    assert calls == ["example.com"]
