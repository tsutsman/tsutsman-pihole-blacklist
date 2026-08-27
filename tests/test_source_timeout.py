from scripts import update_domains


def test_read_source_retries_raw_timeout(monkeypatch):
    attempts = {"count": 0}
    sleeps: list[float] = []

    def fake_urlopen(url, timeout=10):
        attempts["count"] += 1
        raise TimeoutError("read operation timed out")

    monkeypatch.setattr(update_domains, "urlopen", fake_urlopen)
    monkeypatch.setattr(update_domains.time, "sleep", sleeps.append)

    assert update_domains._read_source("https://example.com/feed.txt") is None
    assert attempts["count"] == update_domains.MAX_RETRIES
    assert len(sleeps) == update_domains.MAX_RETRIES - 1
