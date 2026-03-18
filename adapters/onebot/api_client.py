"""Shared OneBot API client implementation."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Callable
from typing import Any

import httpx

from core.adapter import ApiClient, Session
from core.message.message_chain import MessageChain
from core.message.message_components import MessageComponent, Node, Text
from core.toolkit.logger import get_logger


ComponentLike = MessageComponent | str


class OneBotApiClient(ApiClient):
    """Shared API client built on top of a OneBot WebSocket session."""

    def __init__(
        self,
        session: Session,
        *,
        logger: Any | None = None,
        timeout: int = 10,
        readiness_checker: Callable[[], bool] | None = None,
    ) -> None:
        self.session = session
        self.logger = logger or get_logger()
        self.timeout = timeout
        self.readiness_checker = readiness_checker or (lambda: False)
        self.response_callbacks: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def call_api(
        self,
        action: str,
        params: dict[str, Any],
        timeout: int | None = None,
    ) -> dict[str, Any]:
        if not self.readiness_checker():
            self.logger.warning("WebSocket 未连接，无法调用 API。")
            return {
                "status": "failed",
                "retcode": -1,
                "data": None,
                "echo": str(uuid.uuid4()),
            }

        echo = str(uuid.uuid4())
        message = {"action": action, "params": params, "echo": echo}

        future = asyncio.get_running_loop().create_future()
        self.response_callbacks[echo] = future
        await self.session.send(message)

        try:
            return await asyncio.wait_for(future, timeout=timeout or self.timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"调用 API 超时: {action}")
            self.response_callbacks.pop(echo, None)
            return {
                "status": "failed",
                "retcode": 98,
                "data": None,
                "msg": "API call timeout",
                "echo": echo,
            }

    def handle_response(self, data: dict[str, Any]) -> bool:
        if "status" not in data or "echo" not in data:
            return False

        future = self.response_callbacks.pop(data["echo"], None)
        if future and not future.done():
            future.set_result(data)
        return True

    def cancel_pending(self) -> None:
        for future in self.response_callbacks.values():
            if not future.done():
                future.cancel()
        self.response_callbacks.clear()

    async def send_friend_message(self, user_id: int, components: ComponentLike | list[ComponentLike]) -> dict[str, Any]:
        message = self._build_message_chain(components)
        if isinstance(message[0], Node):
            return await self.send_private_forward_msg(user_id, message)
        return await self.call_api("send_private_msg", {"user_id": user_id, "message": message.to_dict()})

    async def send_group_message(self, group_id: int, components: ComponentLike | list[ComponentLike]) -> dict[str, Any]:
        message = self._build_message_chain(components)
        if isinstance(message[0], Node):
            return await self.send_group_forward_msg(group_id, message)
        return await self.call_api("send_group_msg", {"group_id": group_id, "message": message.to_dict()})

    async def send_group_forward_msg(self, group_id: int, components: ComponentLike | list[ComponentLike]) -> dict[str, Any]:
        message = self._build_message_chain(components)
        data = {"group_id": group_id, "messages": message.to_dict()}
        self.logger.info_msg(f"发送消息: {data}")
        return await self.call_api("send_group_forward_msg", data)

    async def send_private_forward_msg(self, user_id: int, components: ComponentLike | list[ComponentLike]) -> dict[str, Any]:
        message = self._build_message_chain(components)
        data = {"user_id": user_id, "messages": message.to_dict()}
        self.logger.info_msg(f"发送消息: {data}")
        return await self.call_api("send_private_forward_msg", data)

    async def get_status(self) -> dict[str, Any]:
        return await self.call_api("get_status", {})

    async def get_forward_msg(self, message_id: str) -> dict[str, Any]:
        return await self.call_api("get_forward_msg", {"id": message_id})

    async def recall(self, message_id: int) -> dict[str, Any]:
        return await self.call_api("delete_msg", {"message_id": message_id})

    async def send_like(self, user_id: int) -> dict[str, Any]:
        return await self.call_api("send_like", {"user_id": user_id, "times": 10})

    async def get_friend_list(self) -> dict[str, Any]:
        return await self.call_api("get_friend_list", {"no_cache": False})

    async def delete_friend(self, user_id: int) -> dict[str, Any]:
        return await self.call_api("delete_friend", {"user_id": user_id})

    async def handle_friend_request(self, flag: str, approve: bool, remark: str) -> dict[str, Any]:
        return await self.call_api("set_friend_add_request", {"flag": flag, "approve": approve, "remark": remark})

    async def set_friend_remark(self, user_id: int, remark: str) -> dict[str, Any]:
        return await self.call_api("set_friend_remark", {"user_id": user_id, "remark": remark})

    async def set_friend_category(self, user_id: int, category_id: int) -> dict[str, Any]:
        return await self.call_api("set_friend_category", {"user_id": user_id, "category_id": category_id})

    async def get_stranger_info(self, user_id: int) -> dict[str, Any]:
        return await self.call_api("get_stranger_info", {"user_id": user_id})

    async def set_qq_avatar(self, file: str) -> dict[str, Any]:
        return await self.call_api("set_qq_avatar", {"file": file})

    async def friend_poke(self, user_id: int) -> dict[str, Any]:
        return await self.call_api("friend_poke", {"user_id": user_id})

    async def upload_private_file(self, user_id: int, file: str, name: str | None = None) -> dict[str, Any]:
        return await self.call_api(
            "upload_private_file",
            {"user_id": user_id, "file": file, "name": name or os.path.basename(file)},
        )

    async def get_group_list(self) -> dict[str, Any]:
        return await self.call_api("get_group_list", {"no_cache": False})

    async def get_group_info(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("get_group_info", {"group_id": group_id})

    async def get_group_member_list(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("get_group_member_list", {"group_id": group_id, "no_cache": True})

    async def get_group_member_info(self, group_id: int, user_id: int) -> dict[str, Any]:
        return await self.call_api("get_group_member_info", {"group_id": group_id, "user_id": user_id})

    async def group_poke(self, group_id: int, user_id: int) -> dict[str, Any]:
        return await self.call_api("group_poke", {"group_id": group_id, "user_id": user_id})

    async def set_group_add_request(self, flag: str, approve: bool, reason: str) -> dict[str, Any]:
        return await self.call_api("set_group_add_request", {"flag": flag, "approve": approve, "reason": reason})

    async def quit(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("set_group_leave", {"group_id": group_id})

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool) -> dict[str, Any]:
        return await self.call_api("set_group_admin", {"group_id": group_id, "user_id": user_id, "enable": enable})

    async def set_group_card(self, group_id: int, user_id: int, card: str) -> dict[str, Any]:
        return await self.call_api("set_group_card", {"group_id": group_id, "user_id": user_id, "card": card})

    async def mute(self, group_id: int, user_id: int, duration: int) -> dict[str, Any]:
        return await self.call_api("set_group_ban", {"group_id": group_id, "user_id": user_id, "duration": duration})

    async def set_group_whole_ban(self, group_id: int, enable: bool) -> dict[str, Any]:
        return await self.call_api("set_group_whole_ban", {"group_id": group_id, "enable": enable})

    async def set_group_name(self, group_id: int, group_name: str) -> dict[str, Any]:
        return await self.call_api("set_group_name", {"group_id": group_id, "group_name": group_name})

    async def set_group_special_title(self, group_id: int, user_id: int, special_title: str) -> dict[str, Any]:
        return await self.call_api(
            "set_group_special_title",
            {"group_id": group_id, "user_id": user_id, "special_title": special_title},
        )

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = True) -> dict[str, Any]:
        return await self.call_api(
            "set_group_kick",
            {"group_id": group_id, "user_id": user_id, "reject_add_request": reject_add_request},
        )

    async def get_group_honor_info(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("get_group_honor_info", {"group_id": group_id})

    async def get_essence_msg_list(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("get_essence_msg_list", {"group_id": group_id})

    async def set_essence_msg(self, message_id: int | str) -> dict[str, Any]:
        return await self.call_api("set_essence_msg", {"message_id": int(message_id)})

    async def delete_essence_msg(self, message_id: int) -> dict[str, Any]:
        return await self.call_api("delete_essence_msg", {"message_id": message_id})

    async def get_group_root_files(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("get_group_root_files", {"group_id": group_id})

    async def upload_group_file(self, group_id: int, file: str, name: str | None = None) -> dict[str, Any]:
        return await self.call_api(
            "upload_group_file",
            {"group_id": group_id, "file": file, "name": name or os.path.basename(file)},
        )

    async def delete_group_file(self, group_id: int, file_id: str) -> dict[str, Any]:
        return await self.call_api("delete_group_file", {"group_id": group_id, "file_id": file_id})

    async def create_group_file_folder(self, group_id: int, name: str) -> dict[str, Any]:
        return await self.call_api("create_group_file_folder", {"group_id": group_id, "name": name})

    async def delete_group_folder(self, group_id: int, folder_id: str) -> dict[str, Any]:
        return await self.call_api("delete_group_folder", {"group_id": group_id, "folder_id": folder_id})

    async def get_group_file_url(self, file_id: str) -> dict[str, Any]:
        return await self.call_api("get_group_file_url", {"file_id": file_id})

    async def _send_group_notice(self, group_id: int, content: str, image: str) -> dict[str, Any]:
        return await self.call_api("_send_group_notice", {"group_id": group_id, "content": content, "image": image})

    async def _get_group_notice(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("_get_group_notice", {"group_id": group_id})

    async def get_group_ignore_add_request(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("get_group_ignore_add_request", {"group_id": group_id})

    async def send_group_sign(self, group_id: int) -> dict[str, Any]:
        return await self.call_api("send_group_sign", {"group_id": group_id})

    async def get_record(self, file: str, out_format: str = "mp3") -> dict[str, Any]:
        return await self.call_api("get_record", {"file": file, "out_format": out_format})

    async def get_video(self, url: str, path: str) -> str:
        async with httpx.AsyncClient(timeout=200) as client:
            response = await client.get(url)
            with open(path, "wb") as file_obj:
                file_obj.write(response.content)
        return path

    def _build_message_chain(self, components: ComponentLike | list[ComponentLike] | MessageChain) -> MessageChain:
        if isinstance(components, MessageChain):
            return components
        if isinstance(components, str):
            components = [Text(components)]
        elif not isinstance(components, list):
            components = [components]
        else:
            components = [
                Text(component) if isinstance(component, str) else component
                for component in components
            ]
        return MessageChain(components)


__all__ = ["OneBotApiClient"]


