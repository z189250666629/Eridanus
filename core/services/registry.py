"""Shared runtime service registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, ClassVar

from core.toolkit.logger import get_logger


@dataclass(slots=True)
class ServiceEntry:
    """One named runtime service published by a plugin or core module."""

    name: str
    service: Any
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    """Process-wide registry for cross-plugin service lookup."""

    _instance: ClassVar["ServiceRegistry | None"] = None
    _instance_lock: ClassVar[RLock] = RLock()

    def __init__(self) -> None:
        self.logger = get_logger("ServiceRegistry")
        self._entries: dict[str, ServiceEntry] = {}
        self._lock = RLock()

    @classmethod
    def get_instance(cls) -> "ServiceRegistry":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def register(
        self,
        name: str,
        service: Any,
        *,
        provider: str = "",
        metadata: dict[str, Any] | None = None,
        overwrite: bool = True,
    ) -> ServiceEntry:
        with self._lock:
            if not overwrite and name in self._entries:
                raise KeyError(f"Service '{name}' already registered.")

            entry = ServiceEntry(
                name=name,
                service=service,
                provider=provider,
                metadata=dict(metadata or {}),
            )
            self._entries[name] = entry
            return entry

    def unregister(self, name: str) -> ServiceEntry | None:
        with self._lock:
            return self._entries.pop(name, None)

    def unregister_by_provider(self, provider: str) -> list[str]:
        with self._lock:
            removed = [
                name
                for name, entry in self._entries.items()
                if entry.provider == provider
            ]
            for name in removed:
                self._entries.pop(name, None)
            return removed

    def get(self, name: str, default: Any = None) -> Any:
        with self._lock:
            entry = self._entries.get(name)
            return entry.service if entry is not None else default

    def get_entry(self, name: str) -> ServiceEntry | None:
        with self._lock:
            entry = self._entries.get(name)
            if entry is None:
                return None
            return ServiceEntry(
                name=entry.name,
                service=entry.service,
                provider=entry.provider,
                metadata=dict(entry.metadata),
            )

    def require(self, name: str) -> Any:
        service = self.get(name)
        if service is None:
            raise KeyError(f"Service '{name}' is not registered.")
        return service

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._entries

    def list_services(self) -> list[ServiceEntry]:
        with self._lock:
            return [
                ServiceEntry(
                    name=entry.name,
                    service=entry.service,
                    provider=entry.provider,
                    metadata=dict(entry.metadata),
                )
                for entry in self._entries.values()
            ]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


def get_service_registry() -> ServiceRegistry:
    return ServiceRegistry.get_instance()


__all__ = ["ServiceEntry", "ServiceRegistry", "get_service_registry"]

