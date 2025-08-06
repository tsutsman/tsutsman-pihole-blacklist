from scripts.check_lists import (
    _find_cross_duplicates,
    _find_duplicates,
    _validate_domains,
    _validate_regexes,
)


def test_find_duplicates():
    assert _find_duplicates(["a", "b", "a"]) == {"a"}


def test_find_cross_duplicates():
    assert _find_cross_duplicates(["a", "b"], ["b", "c"]) == {"b"}


def test_validate_domains():
    assert _validate_domains(["example.com", "bad_domain"]) == ["bad_domain"]


def test_validate_regexes():
    assert _validate_regexes([r"^good$", r"["]) == ["["]
