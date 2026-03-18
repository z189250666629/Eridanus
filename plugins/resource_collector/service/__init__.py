"""Lightweight package entry for resource_collector services.

This package intentionally avoids importing concrete service modules at import time.
Several submodules require runtime config or optional dependencies; importing them
from here would make plugin entry discovery unstable.
"""

__all__ = []
