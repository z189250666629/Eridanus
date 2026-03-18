"""Compatibility wrapper for shared OneBot outbound capability helpers."""

from adapters.onebot.capabilities import ComponentLike, is_lagrange_adapter, normalize_outbound_components


__all__ = [
    "ComponentLike",
    "is_lagrange_adapter",
    "normalize_outbound_components",
]
