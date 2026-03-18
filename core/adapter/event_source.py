"""Incoming event source abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable


EventHandler = Callable[[Any], Awaitable[None]]


class EventSource(ABC):
    """Source of platform events built on top of a shared session."""

    @abstractmethod
    async def start(self, on_event: EventHandler) -> None:
        """Start consuming transport payloads and forward translated events."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop consuming events."""
