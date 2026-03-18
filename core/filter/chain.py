"""Composable filter chain."""

from __future__ import annotations

from typing import Any

from .base import Filter, FilterDecision


class FilterChain:
    """Evaluate filters in order and stop at the first rejection."""

    def __init__(self) -> None:
        self.filters: list[Filter] = []

    def add(self, filter_: Filter) -> None:
        self.filters.append(filter_)

    async def check(self, event: Any) -> FilterDecision:
        for filter_ in self.filters:
            decision = await filter_.check(event)
            if not decision.allowed:
                return decision
        return FilterDecision(True)
