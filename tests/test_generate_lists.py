import json

from scripts import generate_lists


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
