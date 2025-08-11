from scripts.utils import load_entries


def test_load_entries(tmp_path):
    file = tmp_path / "list.txt"
    file.write_text("a.com\n# коментар\n\nB.COM\n")
    assert load_entries(file) == ["a.com", "b.com"]
