"""Runtime services registry."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["ServiceEntry", "ServiceRegistry", "get_service_registry"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = import_module(".registry", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
