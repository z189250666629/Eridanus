"""Filter abstractions used by the composed core bot."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FilterDecision:
    allowed: bool
    reason: str | None = None


class Filter(ABC):
    """Base class for message/event filters."""

    @abstractmethod
    async def check(self, event: Any) -> FilterDecision:
        """Return whether the event should continue through the pipeline."""
