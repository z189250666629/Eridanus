"""Shared OneBot platform adapter."""

from __future__ import annotations

import asyncio
from typing import Any

from core.adapter import EventHandler, PlatformAdapter
from core.message import MessageChain
from core.message.message_components import File, Node, Reply, Text

from .api_client import OneBotApiClient
from .event_source import OneBotEventSource
from .session_ws import OneBotWebSocketSession


class OneBotAdapter(PlatformAdapter):
    """Compose session, event source and API client into a generic OneBot adapter."""

    def __init__(
        self,
        uri: str,
        *,
        logger: Any,
        event_source: OneBotEventSource | None = None,
        api_client: OneBotApiClient | None = None,
        session: OneBotWebSocketSession | None = None,
    ) -> None:
        self.logger = logger
        self.session = session or OneBotWebSocketSession(uri, logger=logger)
        self.api_client = api_client or OneBotApiClient(
            self.session,
            logger=logger,
            readiness_checker=lambda: self.session.websocket is not None,
        )
        self.id = 0
        self.event_source = event_source or OneBotEventSource(
            self.session,
            self.api_client,
            logger=logger,
            on_lifecycle=self._handle_lifecycle_event,
        )
        self._event_task: asyncio.Task | None = None
        self._on_event: EventHandler | None = None

    async def start(self, on_event: EventHandler) -> None:
        self._on_event = on_event
        await self.session.connect()
        if self._event_task is None or self._event_task.done():
            self._event_task = asyncio.create_task(self.event_source.start(on_event))

    async def stop(self) -> None:
        await self.event_source.stop()
        if self._event_task and not self._event_task.done():
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        self._event_task = None
        self.api_client.cancel_pending()
        await self.session.disconnect()

    async def send(self, event: Any, components: Any, quote: bool = False) -> Any:
        component_list = self._normalize_components(components)
        if quote and getattr(event, "message_id", None) is not None:
            component_list.insert(0, Reply(id=event.message_id))

        message_chain = MessageChain(component_list)

        if hasattr(event, "group_id"):
            if isinstance(message_chain[0], Node):
                return await self.api_client.send_group_forward_msg(event.group_id, message_chain)
            if all(isinstance(item, File) for item in message_chain):
                result = None
                for file_component in message_chain:
                    result = await self.api_client.upload_group_file(event.group_id, file_component.file)
                return result
            return await self.api_client.send_group_message(event.group_id, message_chain)

        if hasattr(event, "user_id"):
            if isinstance(message_chain[0], Node):
                return await self.api_client.send_private_forward_msg(event.user_id, message_chain)
            if all(isinstance(item, File) for item in message_chain):
                result = None
                for file_component in message_chain:
                    result = await self.api_client.upload_private_file(event.user_id, file_component.file)
                return result
            return await self.api_client.send_friend_message(event.user_id, message_chain)

        raise ValueError("Unsupported target event for OneBotAdapter.send()")

    async def _handle_lifecycle_event(self, event_obj: Any) -> None:
        try:
            if event_obj.post_type == "meta_event" and event_obj.meta_event_type == "lifecycle":
                self.id = int(event_obj.self_id)
                self.logger.info_msg(f"Bot ID: {self.id}")
        except Exception:
            pass

    def _normalize_components(self, components: Any) -> list[Any]:
        if isinstance(components, MessageChain):
            return list(components)
        if isinstance(components, str):
            return [Text(components)]
        if isinstance(components, list):
            return [Text(component) if isinstance(component, str) else component for component in components]
        return [Text(components) if isinstance(components, str) else components]

    def __getattr__(self, name: str) -> Any:
        return getattr(self.api_client, name)


__all__ = ["OneBotAdapter"]
