"""Platform API client abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ApiClient(ABC):
    """Client responsible for platform-specific API calls."""

    @abstractmethod
    async def call_api(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call one platform API action and return the raw response payload."""
