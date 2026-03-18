"""Composed core bot runtime."""

from __future__ import annotations

from typing import Any

from core.adapter import PlatformAdapter
from core.filter import FilterChain

from .event_bus import EventBus


class Bot:
    """Compose adapter, filters and event bus into one runtime object."""

    def __init__(
        self,
        adapter: PlatformAdapter,
        config: Any,
        *,
        plugin_manager: Any | None = None,
        filter_chain: FilterChain | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.adapter = adapter
        self.config = config
        self.plugin_manager = plugin_manager
        self.filter_chain = filter_chain or FilterChain()
        self.event_bus = event_bus or EventBus()

    async def start(self) -> None:
        await self._start_plugin_manager()
        await self.adapter.start(self._handle_event)

    async def stop(self) -> None:
        await self.adapter.stop()
        await self._stop_plugin_manager()

    def on(self, event_type: Any):
        return self.event_bus.on(event_type)

    async def send(self, event: Any, components: Any, quote: bool = False) -> Any:
        return await self.adapter.send(event, components, quote)

    def set_plugin_manager(self, plugin_manager: Any) -> None:
        self.plugin_manager = plugin_manager

    async def _handle_event(self, event: Any) -> None:
        decision = await self.filter_chain.check(event)
        if decision.allowed:
            await self.event_bus.emit(event)

    async def _start_plugin_manager(self) -> None:
        if self.plugin_manager is None:
            return
        if hasattr(self.plugin_manager, "start"):
            await self.plugin_manager.start()
            return
        if hasattr(self.plugin_manager, "load_all"):
            await self.plugin_manager.load_all()

    async def _stop_plugin_manager(self) -> None:
        if self.plugin_manager is None:
            return
        if hasattr(self.plugin_manager, "stop"):
            await self.plugin_manager.stop()
            return
        if hasattr(self.plugin_manager, "teardown"):
            await self.plugin_manager.teardown()


__all__ = ["Bot"]
