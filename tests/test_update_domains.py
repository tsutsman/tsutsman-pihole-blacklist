import json
import threading
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.error import URLError

from scripts import update_domains


def _source(url: str, **kwargs) -> update_domains.SourceConfig:
    return update_domains.SourceConfig(name=url, url=url, **kwargs)


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
    markdown = tmp_path / "summary.md"
    sources = [_source("a"), _source("b")]
    cache = tmp_path / "cache.json"
    update_domains.update(
        dest=dest,
        chunk_size=1,
        sources=sources,
        report_path=report,
        markdown_path=markdown,
        status_path=status,
        cache_path=cache,
    )
    assert dest.read_text().splitlines() == ["a.com"]
    data = json.loads(report.read_text())
    assert data["added"] == ["a.com"]
    summary = markdown.read_text()
    assert "Нові домени" in summary
    assert "a.com" in summary
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
    markdown = tmp_path / "summary.md"
    cache = tmp_path / "cache.json"
    update_domains.update(
        dest=dest,
        sources=[_source("u1"), _source("u2")],
        report_path=report,
        markdown_path=markdown,
        status_path=status,
        cache_path=cache,
    )
    assert set(calls) == {"u1", "u2"}


def test_update_reports_diagnostics(tmp_path, monkeypatch):
    dest = tmp_path / "domains.txt"
    dest.write_text("0.0.0.0 old.com\nold.com\n192.168.0.1\n")
    report = tmp_path / "report.json"
    status = tmp_path / "status.json"
    markdown = tmp_path / "summary.md"

    def fake_fetch(source):
        return source, ["new.com"]

    monkeypatch.setattr(update_domains, "_fetch", fake_fetch)

    cache = tmp_path / "cache.json"
    update_domains.update(
        dest=dest,
        sources=[_source("src")],
        report_path=report,
        markdown_path=markdown,
        status_path=status,
        cache_path=cache,
    )

    data = json.loads(report.read_text())
    assert data["normalized"]["total"] == 1
    assert data["duplicates_removed"]["total"] == 1
    assert data["duplicates_removed"]["unique"] == 1
    assert data["invalid_lines"]["total"] == 1
    preview = data["normalized"]["preview"][0]
    assert preview["normalized"] == "old.com"
    assert preview["original"] == "0.0.0.0 old.com"
    assert data["duplicates_removed"]["preview"] == ["old.com"]
    assert data["invalid_lines"]["preview"] == ["192.168.0.1"]

    summary = markdown.read_text()
    assert "Нормалізовані записи" in summary
    assert "old.com ← `0.0.0.0 old.com`" in summary
    assert "Видалено дублікати: 1" in summary
    assert "Пропущено некоректних рядків: 1" in summary


def test_update_uses_cached_sources(tmp_path, monkeypatch):
    dest = tmp_path / "domains.txt"
    report = tmp_path / "report.json"
    status = tmp_path / "status.json"
    markdown = tmp_path / "summary.md"
    cache = tmp_path / "cache.json"
    now = datetime.now(timezone.utc)
    cache.write_text(
        json.dumps(
            {
                "http://cached": {
                    "domains": ["cached.com", "cached.com"],
                    "fetched_at": now.isoformat(),
                }
            }
        )
    )

    called = {"value": False}

    def fake_fetch(source):
        called["value"] = True
        return source, ["new.com"]

    monkeypatch.setattr(update_domains, "_fetch", fake_fetch)

    update_domains.update(
        dest=dest,
        sources=[_source("http://cached")],
        report_path=report,
        markdown_path=markdown,
        status_path=status,
        cache_path=cache,
    )

    assert dest.read_text().splitlines() == ["cached.com"]
    assert called["value"] is False


def test_update_refreshes_stale_cache(tmp_path, monkeypatch):
    dest = tmp_path / "domains.txt"
    report = tmp_path / "report.json"
    status = tmp_path / "status.json"
    markdown = tmp_path / "summary.md"
    cache = tmp_path / "cache.json"
    old = datetime.now(timezone.utc) - timedelta(days=5)
    cache.write_text(
        json.dumps(
            {
                "http://stale": {
                    "domains": ["cached.com"],
                    "fetched_at": old.isoformat(),
                }
            }
        )
    )

    def fake_fetch(source):
        return source, ["fresh.com", "fresh.com"]

    monkeypatch.setattr(update_domains, "_fetch", fake_fetch)

    update_domains.update(
        dest=dest,
        sources=[_source("http://stale", update_interval_days=1)],
        report_path=report,
        markdown_path=markdown,
        status_path=status,
        cache_path=cache,
    )

    assert dest.read_text().splitlines() == ["fresh.com"]
    data = json.loads(cache.read_text())
    assert data["http://stale"]["domains"] == ["fresh.com"]


def test_main_passes_args(tmp_path, monkeypatch):
    called: dict[str, object] = {}

    def fake_update(
        *,
        dest,
        chunk_size,
        config_path,
        report_path,
        markdown_path,
        status_path,
        sources=None,
    ):
        called["dest"] = dest
        called["chunk_size"] = chunk_size
        called["config_path"] = config_path
        called["report_path"] = report_path
        called["markdown_path"] = markdown_path
        called["status_path"] = status_path

    monkeypatch.setattr(update_domains, "update", fake_update)
    dest = tmp_path / "out.txt"
    config = tmp_path / "cfg.json"
    report = tmp_path / "report.json"
    markdown = tmp_path / "report.md"
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
            "--markdown-report",
            str(markdown),
            "--status",
            str(status),
        ]
    )
    assert called["dest"] == dest
    assert called["chunk_size"] == 7
    assert called["config_path"] == config
    assert called["report_path"] == report
    assert called["markdown_path"] == markdown
    assert called["status_path"] == status
