import json
from pathlib import Path

import pytest

from scripts import generate_lists
from scripts.utils import EntryMetadata


def _prepare(monkeypatch, tmp_path, *, catalog=None):
    domains = tmp_path / "domains.txt"
    regex = tmp_path / "regex.list"
    catalog_file = tmp_path / "catalog.json"
    domains.write_text("example.com\n")
    regex.write_text("bad.*\n")
    catalog_data = catalog or {"domains": [], "regexes": []}
    catalog_file.write_text(json.dumps(catalog_data, ensure_ascii=False))
    monkeypatch.setattr(generate_lists, "DOMAINS_FILE", domains)
    monkeypatch.setattr(generate_lists, "REGEX_FILE", regex)
    monkeypatch.setattr(generate_lists, "CATALOG_FILE", catalog_file)


def test_generate_default(tmp_path, monkeypatch):
    _prepare(monkeypatch, tmp_path)
    generate_lists.main(["--dist-dir", str(tmp_path)])
    adguard = (tmp_path / "adguard.txt").read_text()
    ublock = (tmp_path / "ublock.txt").read_text()
    assert adguard == "||example.com^\n/bad.*/\n"
    assert ublock == "||example.com^\n/bad.*/\n"
    assert not (tmp_path / "hosts.txt").exists()


def test_generate_hosts(tmp_path, monkeypatch):
    _prepare(monkeypatch, tmp_path)
    generate_lists.main(["--dist-dir", str(tmp_path), "--formats", "hosts"])
    hosts = (tmp_path / "hosts.txt").read_text()
    assert hosts == "0.0.0.0 example.com\n"
    assert not (tmp_path / "adguard.txt").exists()
    assert not (tmp_path / "ublock.txt").exists()


def test_generate_additional_formats_and_segments(tmp_path, monkeypatch):
    catalog = {
        "domains": [
            {
                "value": "example.com",
                "category": "фішинг",
                "regions": ["global"],
                "sources": ["тест"],
                "status": "active",
            }
        ],
        "regexes": [
            {
                "value": "bad.*",
                "category": "фішинг",
                "regions": ["global"],
                "sources": ["тест"],
                "status": "active",
            }
        ],
    }
    _prepare(monkeypatch, tmp_path, catalog=catalog)
    dist = tmp_path / "out"
    generate_lists.main(
        [
            "--dist-dir",
            str(dist),
            "--formats",
            "rpz",
            "dnsmasq",
            "--group-by",
            "category",
        ]
    )
    rpz = (dist / "rpz.txt").read_text().splitlines()
    assert "example.com CNAME ." in rpz
    dnsmasq = (dist / "dnsmasq.conf").read_text().splitlines()
    assert dnsmasq == ["address=/example.com/0.0.0.0"]
    segment = dist / "segments" / "category" / "rpz--фішинг.txt"
    assert segment.exists()
    assert "example.com CNAME ." in segment.read_text().splitlines()


def test_slugify_handles_special_cases():
    assert (
        generate_lists._slugify("Category / Path|Розділ:V2!")
        == "category---path-розділ-v2"
    )
    assert generate_lists._slugify("***") == "segment"


def test_group_entries_supports_all_modes():
    metadata = EntryMetadata(
        value="example.com",
        category="фішинг",
        regions=("ua", "global"),
        sources=("збір",),
    )
    entries = [("example.com", metadata), ("orphan.com", None)]
    all_groups = generate_lists._group_entries(entries, group_by=None)
    assert all_groups == {"усі": ["example.com", "orphan.com"]}
    by_category = generate_lists._group_entries(entries, group_by="category")
    assert by_category["фішинг"] == ["example.com"]
    assert by_category[generate_lists.DEFAULT_SEGMENT_NAME] == ["orphan.com"]
    by_region = generate_lists._group_entries(entries, group_by="region")
    assert set(by_region) == {"ua", "global", generate_lists.DEFAULT_SEGMENT_NAME}
    by_source = generate_lists._group_entries(entries, group_by="source")
    assert set(by_source) == {"збір", generate_lists.DEFAULT_SEGMENT_NAME}


def test_generate_skips_empty_segment_groups(tmp_path, monkeypatch):
    catalog = {
        "domains": [
            {
                "value": "example.com",
                "category": "фішинг",
                "regions": ["ua"],
                "sources": ["тест"],
                "status": "active",
            }
        ],
        "regexes": [
            {
                "value": "bad.*",
                "category": "фішинг",
                "regions": ["ua"],
                "sources": ["тест"],
                "status": "active",
            }
        ],
    }
    _prepare(monkeypatch, tmp_path, catalog=catalog)
    dist = tmp_path / "dist"
    generate_lists.generate(
        dist_dir=dist,
        formats=["unbound", "hosts"],
        group_by="source",
    )
    segment_dir = dist / "segments" / "source"
    unbound_segments = list(segment_dir.glob("unbound--*.conf"))
    assert len(unbound_segments) == 1
    assert "example.com" in unbound_segments[0].read_text()
    hosts_segments = list(segment_dir.glob("hosts--*.txt"))
    assert len(hosts_segments) == 1


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["--include-inactive"], True),
        (["--statuses", "inactive"], False),
    ],
)
def test_main_parses_boolean_flags(tmp_path, monkeypatch, argv, expected):
    called: dict[str, object] = {}

    def fake_generate(**kwargs):
        called.update(kwargs)

    monkeypatch.setattr(generate_lists, "generate", fake_generate)
    argv = ["--dist-dir", str(tmp_path)] + argv
    generate_lists.main(argv)
    assert called["include_inactive"] is expected
