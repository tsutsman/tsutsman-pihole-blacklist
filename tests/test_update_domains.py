import threading
from urllib.error import URLError
from scripts import update_domains


def test_fetch_handles_error(monkeypatch):
    def fake_urlopen(url, timeout=10):
        raise URLError("boom")

    monkeypatch.setattr(update_domains, "urlopen", fake_urlopen)
    assert update_domains._fetch("http://example.com") == []


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
    assert update_domains._fetch("http://example.com") == [
        "example.com",
        "example.org",
    ]


def test_update_chunk_size(tmp_path, monkeypatch):
    monkeypatch.setattr(update_domains, "_fetch", lambda url: [f"{url}.com"])
    dest = tmp_path / "domains.txt"
    update_domains.update(dest=dest, chunk_size=1, sources=["a", "b"])
    assert dest.read_text().splitlines() == ["a.com"]


def test_update_parallel_fetch(tmp_path, monkeypatch):
    barrier = threading.Barrier(2)
    calls: list[str] = []

    def fake_fetch(url):
        calls.append(url)
        barrier.wait(timeout=1)
        return []

    monkeypatch.setattr(update_domains, "_fetch", fake_fetch)
    dest = tmp_path / "domains.txt"
    update_domains.update(dest=dest, sources=["u1", "u2"])
    assert set(calls) == {"u1", "u2"}
