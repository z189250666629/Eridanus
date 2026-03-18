"""Shared OneBot event source implementation."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from core.adapter import EventHandler, EventSource, Session

from .event_factory import OneBotEventFactory


class OneBotEventSource(EventSource):
    """Decode transport payloads and dispatch OneBot-compatible events."""

    def __init__(
        self,
        session: Session,
        api_client: Any,
        *,
        logger: Any,
        on_lifecycle: Any | None = None,
        unmatched_event_message: str = "无法匹配事件类型，跳过处理。",
        unknown_message_message: str = "收到未知消息格式，已忽略。",
    ) -> None:
        self.session = session
        self.api_client = api_client
        self.logger = logger
        self.on_lifecycle = on_lifecycle
        self.unmatched_event_message = unmatched_event_message
        self.unknown_message_message = unknown_message_message
        self._running = False

    async def start(self, on_event: EventHandler) -> None:
        self._running = True
        try:
            while self._running:
                payload = await self.session.recv()
                await self.process_payload(payload, on_event)
        except asyncio.CancelledError:
            raise

    async def stop(self) -> None:
        self._running = False

    async def process_payload(self, payload: str, on_event: EventHandler) -> None:
        data = json.loads(payload)
        self.logger.info_msg(f"收到服务端响应: {data}")

        if self.api_client.handle_response(data):
            return

        if "post_type" not in data:
            self.logger.warning(self.unknown_message_message)
            return

        event_obj = OneBotEventFactory.create_event(data)
        if event_obj is None:
            self.logger.warning(self.unmatched_event_message)
            return

        if self.on_lifecycle is not None:
            await self.on_lifecycle(event_obj)

        await on_event(event_obj)


__all__ = ["OneBotEventSource"]
