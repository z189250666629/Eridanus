"""Transport session abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Session(ABC):
    """Shared transport session used by event and API layers."""

    @abstractmethod
    async def connect(self) -> None:
        """Open the underlying transport connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the underlying transport connection."""

    @abstractmethod
    async def recv(self) -> Any:
        """Receive one raw payload from the transport."""

    @abstractmethod
    async def send(self, payload: Any) -> None:
        """Send one raw payload through the transport."""
