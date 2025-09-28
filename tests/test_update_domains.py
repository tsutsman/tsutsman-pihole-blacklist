import json
import threading
from urllib.error import HTTPError
from urllib.error import URLError

from scripts import update_domains


def _source(url: str) -> update_domains.SourceConfig:
    return update_domains.SourceConfig(name=url, url=url)


def test_fetch_handles_error(monkeypatch):
    def fake_urlopen(url, timeout=10):
        raise URLError("boom")

    monkeypatch.setattr(update_domains, "urlopen", fake_urlopen)
    source = _source("http://example.com")
    assert update_domains._fetch(source) == (source, [])


def test_fetch_parses_domains(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"127.0.0.1 example.com\n#c\nexample.org\n"

    monkeypatch.setattr(
        update_domains,
        "urlopen",
        lambda url, timeout=10: FakeResp(),
    )
    source = _source("http://example.com")
    assert update_domains._fetch(source) == (
        source,
        ["example.com", "example.org"],
    )


def test_fetch_normalizes_hosts(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                "0.0.0.0 example.com\n"
                "127.0.0.1foo.com\n"
                "0.0.0.0bar.com\n"
                "%20mandrillapp.com\n"
                "*.wildcard.com\n"
                "192.168.1.1\n"
            ).encode()

    monkeypatch.setattr(
        update_domains,
        "urlopen",
        lambda url, timeout=10: FakeResp(),
    )
    source = _source("http://example.com")

    assert update_domains._fetch(source) == (
        source,
        [
            "example.com",
            "foo.com",
            "bar.com",
            "mandrillapp.com",
            "wildcard.com",
        ],
    )


def test_fetch_retries_rate_limit(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"example.com\n"

    attempts = {"count": 0}

    def fake_urlopen(url, timeout=10):
        if attempts["count"] == 0:
            attempts["count"] += 1
            raise HTTPError(url, 429, "Too Many Requests", {"Retry-After": "2"}, None)
        attempts["count"] += 1
        return FakeResp()

    sleeps: list[float] = []

    monkeypatch.setattr(update_domains, "urlopen", fake_urlopen)
    monkeypatch.setattr(update_domains.time, "sleep", sleeps.append)

    source = _source("http://example.com")

    assert update_domains._fetch(source) == (source, ["example.com"])
    assert attempts["count"] == 2
    assert sleeps == [2.0]


def test_update_chunk_size(tmp_path, monkeypatch):
    def fake_fetch(source):
        return source, [f"{source.name}.com"]

    monkeypatch.setattr(update_domains, "_fetch", fake_fetch)
    dest = tmp_path / "domains.txt"
    report = tmp_path / "report.json"
    status = tmp_path / "status.json"
    sources = [_source("a"), _source("b")]
    update_domains.update(
        dest=dest,
        chunk_size=1,
        sources=sources,
        report_path=report,
        status_path=status,
    )
    assert dest.read_text().splitlines() == ["a.com"]
    data = json.loads(report.read_text())
    assert data["added"] == ["a.com"]
    status_data = json.loads(status.read_text())
    assert status_data["a.com"]["status"] == "active"


def test_update_parallel_fetch(tmp_path, monkeypatch):
    barrier = threading.Barrier(2)
    calls: list[str] = []

    def fake_fetch(source):
        calls.append(source.name)
        barrier.wait(timeout=1)
        return source, []

    monkeypatch.setattr(update_domains, "_fetch", fake_fetch)
    dest = tmp_path / "domains.txt"
    report = tmp_path / "report.json"
    status = tmp_path / "status.json"
    update_domains.update(
        dest=dest,
        sources=[_source("u1"), _source("u2")],
        report_path=report,
        status_path=status,
    )
    assert set(calls) == {"u1", "u2"}


def test_main_passes_args(tmp_path, monkeypatch):
    called: dict[str, object] = {}

    def fake_update(*, dest, chunk_size, config_path, report_path, status_path, sources=None):
        called["dest"] = dest
        called["chunk_size"] = chunk_size
        called["config_path"] = config_path
        called["report_path"] = report_path
        called["status_path"] = status_path

    monkeypatch.setattr(update_domains, "update", fake_update)
    dest = tmp_path / "out.txt"
    config = tmp_path / "cfg.json"
    report = tmp_path / "report.json"
    status = tmp_path / "status.json"
    update_domains.main(
        [
            "--chunk-size",
            "7",
            "--dest",
            str(dest),
            "--config",
            str(config),
            "--report",
            str(report),
            "--status",
            str(status),
        ]
    )
    assert called["dest"] == dest
    assert called["chunk_size"] == 7
    assert called["config_path"] == config
    assert called["report_path"] == report
    assert called["status_path"] == status
