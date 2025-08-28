import scripts.check_lists as check_lists
from scripts.check_lists import (
    _find_cross_duplicates,
    _find_duplicates,
    _validate_domains,
    _validate_regexes,
    main,
)


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


def test_main(tmp_path, monkeypatch, capsys):
    domains = tmp_path / "domains.txt"
    regex = tmp_path / "regex.list"
    domains.write_text("example.com\n")
    regex.write_text(r"good.*\n")
    monkeypatch.setattr(check_lists, "DOMAINS_FILE", domains)
    monkeypatch.setattr(check_lists, "REGEX_FILE", regex)
    assert main() == 0
    assert capsys.readouterr().out.strip() == "Списки коректні"


def test_main_invalid(tmp_path, monkeypatch, capsys):
    domains = tmp_path / "domains.txt"
    regex = tmp_path / "regex.list"
    domains.write_text("bad_domain\n")
    regex.write_text("[\n")
    monkeypatch.setattr(check_lists, "DOMAINS_FILE", domains)
    monkeypatch.setattr(check_lists, "REGEX_FILE", regex)
    assert main() == 1
    out = capsys.readouterr().out
    assert "Некоректні домени" in out
    assert "Некоректні регулярні вирази" in out
