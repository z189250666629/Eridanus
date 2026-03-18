"""Legacy-style HTTP bot hosted under the new adapter package."""

from __future__ import annotations

import asyncio
from typing import Type

import uvicorn
from fastapi import FastAPI, Request

from core.bot.event_bus import EventBus
from core.event.base import EventBase
from core.event.factory import EventFactory
from core.toolkit.logger import get_logger

from .http_mailman import http_mailman


class HTTPBot(http_mailman):
    def __init__(self, http_sever, access_token="", host="0.0.0.0", port=8000):
        super().__init__(http_sever, access_token)
        self.logger = get_logger()
        self.event_bus = EventBus(enable_monitoring=False)
        self.host = host
        self.port = port
        self.echo_dict = {}
        self.app = FastAPI()
        self._register_routes()

    def _register_routes(self):
        @self.app.post("/")
        async def root(request: Request):
            data = await request.json()
            await asyncio.create_task(self.receive(data))
            return {"status": "success"}

    def on(self, event: Type[EventBase]):
        return self.event_bus.on(event)

    async def receive(self, data: dict):
        self.logger.info(f"收到消息: {data}")
        event_obj = EventFactory.create_event(data)
        if event_obj:
            await self.event_bus.emit(event_obj)
        else:
            self.logger.warning("无法匹配事件类型，跳过处理。")

    def run(self):
        start_up = {
            "time": 1735098202,
            "self_id": 919467430,
            "post_type": "meta_event",
            "meta_event_type": "startUp",
            "status": {"online": True, "good": True},
            "interval": 30000,
        }
        event_obj = EventFactory.create_event(start_up)
        asyncio.run(self.event_bus.emit(event_obj))
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="warning")


__all__ = ["HTTPBot"]

