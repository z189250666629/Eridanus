"""Platform adapter abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable


EventHandler = Callable[[Any], Awaitable[None]]


class PlatformAdapter(ABC):
    """Platform-facing adapter used by the composed core bot."""

    @abstractmethod
    async def start(self, on_event: EventHandler) -> None:
        """Start the adapter and deliver incoming events through `on_event`."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the adapter and release underlying resources."""

    @abstractmethod
    async def send(self, event: Any, components: Any, quote: bool = False) -> Any:
        """Send message components to the target represented by `event`."""
