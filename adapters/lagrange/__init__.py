"""Compatibility exports for legacy Lagrange-specific imports."""

from adapters.onebot import (
    ComponentLike,
    LagrangeAdapter,
    LagrangeApiClient,
    is_lagrange_adapter,
    normalize_outbound_components,
)

__all__ = [
    "ComponentLike",
    "LagrangeAdapter",
    "LagrangeApiClient",
    "is_lagrange_adapter",
    "normalize_outbound_components",
]
