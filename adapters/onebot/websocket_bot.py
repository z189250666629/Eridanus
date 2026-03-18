"""Legacy-style WebSocket bot hosted under the new OneBot adapter package."""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Union

import httpx
import websockets

from core.bot.event_bus import EventBus
from core.event.base import EventBase
from core.message.message_chain import MessageChain
from core.message.message_components import File, MessageComponent, Node, Reply, Text
from core.message.cq_parser import parse_message_2processed_message
from core.toolkit.logger import get_logger

from . import OneBotApiClient, OneBotEventFactory, OneBotEventSource, OneBotWebSocketSession


class WebSocketBot:
    """Backward-compatible bot facade over the shared OneBot transport pieces."""

    API_CLIENT_METHODS = [
        "create_group_file_folder",
        "delete_essence_msg",
        "delete_friend",
        "delete_group_file",
        "delete_group_folder",
        "friend_poke",
        "get_essence_msg_list",
        "get_forward_msg",
        "get_friend_list",
        "get_group_file_url",
        "get_group_honor_info",
        "get_group_ignore_add_request",
        "get_group_info",
        "get_group_list",
        "get_group_member_info",
        "get_group_member_list",
        "get_group_root_files",
        "get_record",
        "get_status",
        "get_stranger_info",
        "get_video",
        "group_poke",
        "handle_friend_request",
        "mute",
        "quit",
        "recall",
        "send_friend_message",
        "send_group_forward_msg",
        "send_group_message",
        "send_group_sign",
        "send_like",
        "send_private_forward_msg",
        "set_essence_msg",
        "set_friend_category",
        "set_friend_remark",
        "set_group_add_request",
        "set_group_admin",
        "set_group_card",
        "set_group_kick",
        "set_group_name",
        "set_group_special_title",
        "set_group_whole_ban",
        "set_qq_avatar",
        "upload_group_file",
        "upload_private_file",
        "_get_group_notice",
        "_send_group_notice",
    ]

    def __init__(
        self,
        uri: str,
        blocked_loggers=None,
        enable_monitoring: bool = True,
        handler_timeout_warning: float = 10.0,
    ):
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.logger = get_logger(blocked_loggers=blocked_loggers)
        self.session = OneBotWebSocketSession(uri, logger=self.logger)
        self.event_bus = EventBus(
            handler_timeout_warning=handler_timeout_warning,
            enable_monitoring=enable_monitoring,
        )
        self.receive_task: Optional[asyncio.Task] = None
        self._message_queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._set_api_client(
            OneBotApiClient(
                self.session,
                logger=self.logger,
                readiness_checker=lambda: self.session.websocket is not None or self.receive_task is not None,
            )
        )
        self.event_source = OneBotEventSource(
            self.session,
            self.api_client,
            logger=self.logger,
            on_lifecycle=self._handle_lifecycle_event,
        )

    async def _receive(self):
        try:
            while True:
                response = await self.session.recv()
                self.websocket = self.session.websocket
                await self._message_queue.put(response)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.logger.error(f"接收消息时发生错误: {exc}", exc_info=True)
        finally:
            self.api_client.cancel_pending()
            self.receive_task = None

    async def _process_messages(self):
        try:
            while True:
                try:
                    response = await self._message_queue.get()
                    await self.event_source.process_payload(response, self._handle_incoming_event)
                    self._message_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    self.logger.error(f"处理消息时发生错误: {exc}", exc_info=True)
        except asyncio.CancelledError:
            pass
        finally:
            self._processing_task = None

    async def _connect_and_run(self):
        await self._connect()
        if self.websocket:
            self.receive_task = asyncio.create_task(self._receive())
            self._processing_task = asyncio.create_task(self._process_messages())

            try:
                await self.receive_task
            except Exception as exc:
                self.logger.error(f"接收任务出错: {exc}")
            finally:
                if self._processing_task and not self._processing_task.done():
                    self._processing_task.cancel()

    async def _connect(self):
        await self.session.connect()
        self.websocket = self.session.websocket

    async def _call_api(self, action: str, params: dict, timeout: int = 10) -> dict:
        return await self.api_client.call_api(action, params, timeout)

    def run(self):
        asyncio.run(self._connect_and_run())

    def on(self, event):
        return self.event_bus.on(event)

    def _set_api_client(self, api_client, extra_methods=None):
        self.api_client = api_client
        self.response_callbacks = self.api_client.response_callbacks
        if hasattr(self, "event_source"):
            self.event_source.api_client = api_client
        self._bind_api_client_methods(extra_methods)

    def _bind_api_client_methods(self, extra_methods=None):
        delegated_methods = list(self.API_CLIENT_METHODS)
        if extra_methods:
            delegated_methods.extend(extra_methods)
        for method_name in delegated_methods:
            setattr(self, method_name, getattr(self.api_client, method_name))

    async def _handle_lifecycle_event(self, event_obj):
        try:
            if event_obj.post_type == "meta_event" and event_obj.meta_event_type == "lifecycle":
                self.id = int(event_obj.self_id)
                self.logger.info_msg(f"Bot ID: {self.id}")
        except Exception:
            pass

    async def _handle_incoming_event(self, event_obj):
        asyncio.create_task(self.event_bus.emit(event_obj))

    async def send_to_server(self, event: EventBase, message: Union[MessageChain, dict]):
        try:
            if self.session.websocket is not None or self.receive_task is not None:
                if hasattr(event, "group_id"):
                    action = "send_group_msg"
                    params = {"group_id": event.group_id, "message": message.to_dict()}

                    if isinstance(message[0], Node):
                        return await self.send_group_forward_msg(event.group_id, message)
                    if all(isinstance(item, File) for item in message):
                        result = None
                        for file_component in message:
                            result = await self.upload_group_file(event.group_id, file_component.file)
                        return result
                elif hasattr(event, "user_id"):
                    action = "send_private_msg"
                    params = {"user_id": event.user_id, "message": message.to_dict()}

                    if isinstance(message[0], Node):
                        return await self.send_private_forward_msg(event.user_id, message)
                    if all(isinstance(item, File) for item in message):
                        result = None
                        for file_component in message:
                            result = await self.upload_private_file(event.user_id, file_component.file)
                        return result
                self.logger.info_func(f"发送的消息: {message.to_dict()}")
                return await self._call_api(action, params)
            self.logger.warning("WebSocket 未连接，无法发送消息")
        except Exception as exc:
            self.logger.error(f"发送消息时出现错误: {exc}", exc_info=True)

    async def send(self, event: EventBase, components: list[Union[MessageComponent, str]], Quote: bool = False):
        try:
            if isinstance(components, str):
                components = [Text(components)]
            if not isinstance(components, list):
                components = [components]
            if Quote:
                components.insert(0, Reply(id=event.message_id))
            else:
                components = [Text(component) if isinstance(component, str) else component for component in components]

            message_chain = MessageChain(components)
            return await self.send_to_server(event, message_chain)
        except Exception as exc:
            self.logger.error(f"发送消息时出现错误: {exc}", exc_info=True)

    async def get_msg(self, message_id: int):
        source_msg = await self._call_api("get_msg", {"message_id": message_id})
        if source_msg["data"].get("post_type") is None:
            source_msg["data"]["post_type"] = "message"
        if source_msg["data"].get("sub_type") is None:
            source_msg["data"]["sub_type"] = "normal"
        if source_msg["data"].get("font") is None:
            source_msg["data"]["font"] = 0
        if source_msg["data"].get("user_id") is None:
            source_msg["data"]["user_id"] = source_msg["data"]["sender"]["user_id"]
        if source_msg["data"].get("group_id") is None:
            source_msg["data"]["group_id"] = 0
        event_obj = OneBotEventFactory.create_event(source_msg["data"])
        if hasattr(event_obj, "processed_message") and event_obj.processed_message == []:
            event_obj.processed_message = parse_message_2processed_message(event_obj.message)
        return event_obj

    async def get_video(self, url: str, path: str):
        async with httpx.AsyncClient(timeout=200) as client:
            response = await client.get(url)
            with open(path, "wb") as file_obj:
                file_obj.write(response.content)
        return path


__all__ = ["WebSocketBot"]

