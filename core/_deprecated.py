"""Helpers for legacy compatibility warnings."""

from __future__ import annotations

import warnings

_warned_paths: set[str] = set()


def warn_legacy_import(legacy_path: str, replacement: str) -> None:
    """Emit a deprecation warning for legacy import paths once per process."""

    warning_key = f"{legacy_path}->{replacement}"
    if warning_key in _warned_paths:
        return

    warnings.warn(
        f"`{legacy_path}` is deprecated and will be removed in a future release; "
        f"use `{replacement}` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    _warned_paths.add(warning_key)
