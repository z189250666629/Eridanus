"""Shared OneBot WebSocket session implementation."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import websockets
from websockets.protocol import State

from core.adapter import Session
from core.toolkit.logger import get_logger


class OneBotWebSocketSession(Session):
    """Shared WebSocket session used by OneBot-compatible adapters."""

    def __init__(
        self,
        uri: str,
        *,
        reconnect_delay: float = 5.0,
        logger: Any | None = None,
    ) -> None:
        self.uri = uri
        self.reconnect_delay = reconnect_delay
        self.logger = logger or get_logger()
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self._connect_lock = asyncio.Lock()
        self._closing = False

    async def connect(self) -> None:
        self._closing = False
        await self._ensure_connected()

    async def disconnect(self) -> None:
        self._closing = True
        await self._reset_websocket()

    async def recv(self) -> Any:
        while not self._closing:
            websocket = await self._ensure_connected()
            try:
                return await websocket.recv()
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed as exc:
                await self._handle_disconnect(exc)
        raise RuntimeError("WebSocket session is closed.")

    async def send(self, payload: Any) -> None:
        message = payload if isinstance(payload, (bytes, str)) else json.dumps(payload)

        while not self._closing:
            websocket = await self._ensure_connected()
            try:
                await websocket.send(message)
                return
            except asyncio.CancelledError:
                raise
            except websockets.exceptions.ConnectionClosed as exc:
                await self._handle_disconnect(exc)
        raise RuntimeError("WebSocket session is closed.")

    async def _ensure_connected(self) -> websockets.WebSocketClientProtocol:
        if self._is_connected():
            return self.websocket

        async with self._connect_lock:
            while not self._closing and not self._is_connected():
                try:
                    self.websocket = await websockets.connect(self.uri, max_size=None)
                    self.logger.info_msg("WebSocket 连接已建立")
                except Exception as exc:
                    self.logger.error(f"WebSocket 连接出现错误: {exc}")
                    self.logger.warning(f"WebSocket 连接失败，{self.reconnect_delay:g}秒后尝试重连")
                    await asyncio.sleep(self.reconnect_delay)

        if self.websocket is None:
            raise RuntimeError("WebSocket session is not available.")
        return self.websocket

    async def _handle_disconnect(self, exc: Exception) -> None:
        if self._closing:
            return
        self.logger.warning(f"WebSocket 连接关闭: {exc}")
        self.logger.warning(f"{self.reconnect_delay:g}秒后尝试重连")
        await self._reset_websocket()
        await asyncio.sleep(self.reconnect_delay)

    async def _reset_websocket(self) -> None:
        websocket = self.websocket
        self.websocket = None
        if websocket is None:
            return
        try:
            await websocket.close()
        except Exception:
            pass

    def _is_connected(self) -> bool:
        websocket = self.websocket
        if websocket is None:
            return False

        closed = getattr(websocket, "closed", None)
        if closed is not None:
            return not closed

        state = getattr(websocket, "state", None)
        if state is not None:
            return state is State.OPEN

        close_code = getattr(websocket, "close_code", None)
        return close_code is None


__all__ = ["OneBotWebSocketSession"]

