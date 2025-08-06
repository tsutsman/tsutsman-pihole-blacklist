"""Допоміжні функції для роботи зі списками."""
from __future__ import annotations

from pathlib import Path


def load_entries(path: Path) -> list[str]:
    """Читає файл, повертаючи лише непорожні рядки без коментарів."""
    entries: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries
