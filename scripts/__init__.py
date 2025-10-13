"""Загальний простір імен для CLI-скриптів із ледачим імпортом.

Shared namespace for CLI scripts with lazy imports.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

__all__ = [
    "audit_lists",
    "check_lists",
    "generate_lists",
    "diff_reports",
    "update_domains",
    "validate_catalog",
    "utils",
]

if TYPE_CHECKING:  # pragma: no cover
    from . import (  # noqa: F401
        audit_lists,
        check_lists,
        diff_reports,
        generate_lists,
        update_domains,
        utils,
        validate_catalog,
    )


def _load_module(name: str) -> ModuleType:
    module = import_module(f".{name}", __name__)
    globals()[name] = module
    return module


def __getattr__(name: str) -> ModuleType:
    if name in __all__:
        return _load_module(name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:  # pragma: no cover - використовується інтерактивно
    return sorted(set(globals()) | set(__all__))
