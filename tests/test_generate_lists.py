from scripts import generate_lists


def _prepare(monkeypatch, tmp_path):
    domains = tmp_path / "domains.txt"
    regex = tmp_path / "regex.list"
    domains.write_text("example.com\n")
    regex.write_text("bad.*\n")
    monkeypatch.setattr(generate_lists, "DOMAINS_FILE", domains)
    monkeypatch.setattr(generate_lists, "REGEX_FILE", regex)


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
