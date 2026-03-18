"""Legacy-style OneBot HTTP sender hosted under the new adapter package."""

from __future__ import annotations

from typing import Union

import httpx
import requests

from core.event.base import EventBase
from core.message.message_chain import MessageChain
from core.message.message_components import MessageComponent, Node, Reply, Text
from core.toolkit.logger import get_logger


class http_mailman:
    def __init__(self, http_server, access_token=""):
        self.http_server = http_server
        self.logger = get_logger()
        self.headers = {"Authorization": f"Bearer {access_token}"}
        try:
            self.info = self.get_login_info()
        except Exception:
            self.info = None

    async def get_status(self):
        url = f"{self.http_server}/get_status"
        async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
            response = await client.post(url)
            self.logger.info(f"状态: {response.json()}")

    async def send_group_forward_msg(self, group_id: int, components: Union[str, list[Union[MessageComponent, str]]]):
        message = self._build_message_chain(components)
        data = {"group_id": group_id, "messages": message.to_dict()}
        self.logger.info(f"发送消息: {data}")
        url = f"{self.http_server}/send_group_forward_msg"
        async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
            response = await client.post(url, json=data)
            return response.json()

    async def send_private_forward_msg(self, user_id: int, components: Union[str, list[Union[MessageComponent, str]]]):
        message = self._build_message_chain(components)
        data = {"user_id": user_id, "messages": message.to_dict()}
        self.logger.info(f"发送消息: {data}")
        url = f"{self.http_server}/send_private_forward_msg"
        async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
            response = await client.post(url, json=data)
            return response.json()

    async def send_to_server(self, event: EventBase, message: Union[MessageChain, dict]):
        try:
            if hasattr(event, "group_id"):
                data = {"group_id": event.group_id, "message": message.to_dict()}
                if isinstance(message[0], Node):
                    return await self.send_group_forward_msg(event.group_id, message)
                url = f"{self.http_server}/send_group_msg"
            else:
                data = {"user_id": event.user_id, "message": message.to_dict()}
                if isinstance(message[0], Node):
                    return await self.send_private_forward_msg(event.user_id, message)
                url = f"{self.http_server}/send_private_msg"
            self.logger.info(f"发送消息: {data}")
            async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
                response = await client.post(url, json=data)
                return response.json()
        except Exception as exc:
            self.logger.error(f"发送消息时出现错误: {exc}", exc_info=True)

    async def send(self, event: EventBase, components: Union[str, list[Union[MessageComponent, str]]], Quote: bool = False):
        if isinstance(components, str):
            components = [Text(components)]
        if not isinstance(components, list):
            components = [components]
        if Quote:
            components.append(Reply(id=event.message_id))
        else:
            components = [Text(component) if isinstance(component, str) else component for component in components]

        return await self.send_to_server(event, MessageChain(components))

    async def send_friend_message(self, user_id: int, components: Union[str, list[Union[MessageComponent, str]]]):
        message = self._build_message_chain(components)
        data = {"user_id": user_id, "message": message.to_dict()}
        self.logger.info(f"发送消息: {data}")
        url = f"{self.http_server}/send_private_msg"
        async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
            response = await client.post(url, json=data)
            return response.json()

    async def send_group_message(self, group_id: int, components: Union[str, list[Union[MessageComponent, str]]]):
        message = self._build_message_chain(components)
        data = {"group_id": group_id, "message": message.to_dict()}
        self.logger.info(f"发送消息: {data}")
        url = f"{self.http_server}/send_group_msg"
        async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
            response = await client.post(url, json=data)
            return response.json()

    async def recall(self, message_id: int):
        return await self._post("delete_msg", {"message_id": message_id})

    async def send_like(self, user_id):
        return await self._post("send_like", {"user_id": user_id, "times": 10})

    async def get_friend_list(self):
        return await self._post("get_friend_list", {"no_cache": False})

    async def delete_friend(self, user_id):
        return await self._post("delete_friend", {"user_id": user_id})

    async def handle_friend_request(self, flag: str, approve: bool, remark: str):
        return await self._post("set_friend_add_request", {"flag": flag, "approve": approve, "remark": remark})

    async def set_friend_remark(self, user_id: int, remark: str):
        return await self._post("set_friend_remark", {"user_id": user_id, "remark": remark})

    async def set_friend_category(self, user_id: int, category_id: int):
        return await self._post("set_friend_category", {"user_id": user_id, "category_id": category_id})

    async def get_stranger_info(self, user_id: int):
        return await self._post("get_stranger_info", {"user_id": user_id})

    async def set_qq_avatar(self, file: str):
        return await self._post("set_qq_avatar", {"file": file})

    async def friend_poke(self, user_id: int):
        return await self._post("friend_poke", {"user_id": user_id})

    async def upload_private_file(self, user_id: int, file: str, name: str):
        return await self._post("upload_private_file", {"user_id": user_id, "file": file, "name": name})

    async def get_group_list(self):
        return await self._post("get_group_list", {"no_cache": False})

    async def get_group_info(self, group_id: int):
        return await self._post("get_group_info", {"group_id": group_id})

    async def get_group_member_list(self, group_id: int):
        return await self._post("get_group_member_list", {"group_id": group_id, "no_cache": True})

    async def get_group_member_info(self, group_id: int, user_id: int):
        return await self._post("get_group_member_info", {"group_id": group_id, "user_id": user_id})

    async def group_poke(self, group_id: int, user_id: int):
        return await self._post("group_poke", {"group_id": group_id, "user_id": user_id})

    async def set_group_add_request(self, flag: str, approve: bool, reason: str):
        return await self._post("set_group_add_request", {"flag": flag, "approve": approve, "reason": reason})

    async def quit(self, group_id: int):
        return await self._post("set_group_leave", {"group_id": group_id})

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool):
        return await self._post("set_group_admin", {"group_id": group_id, "user_id": user_id, "enable": enable})

    async def set_group_card(self, group_id: int, user_id: int, card: str):
        return await self._post("set_group_card", {"group_id": group_id, "user_id": user_id, "card": card})

    async def mute(self, group_id: int, user_id: int, duration: int):
        return await self._post("set_group_ban", {"group_id": group_id, "user_id": user_id, "duration": duration})

    async def set_group_whole_ban(self, group_id: int, enable: bool):
        return await self._post("set_group_whole_ban", {"group_id": group_id, "enable": enable})

    async def set_group_name(self, group_id: int, group_name: str):
        return await self._post("set_group_name", {"group_id": group_id, "group_name": group_name})

    async def set_group_special_title(self, group_id: int, user_id: int, special_title: str):
        return await self._post(
            "set_group_special_title",
            {"group_id": group_id, "user_id": user_id, "special_title": special_title},
        )

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = True):
        return await self._post(
            "set_group_kick",
            {"group_id": group_id, "user_id": user_id, "reject_add_request": reject_add_request},
        )

    async def get_group_honor_info(self, group_id: int):
        return await self._post("get_group_honor_info", {"group_id": group_id})

    async def get_essence_msg_list(self, group_id: int):
        return await self._post("get_essence_msg_list", {"group_id": group_id})

    async def set_essence_msg(self, message_id: int):
        return await self._post("set_essence_msg", {"message_id": message_id})

    async def delete_essence_msg(self, message_id: int):
        return await self._post("delete_essence_msg", {"message_id": message_id})

    async def get_group_root_files(self, group_id: int):
        return await self._post("get_group_root_files", {"group_id": group_id})

    async def upload_group_file(self, group_id: int, file: str, name: str):
        return await self._post("upload_group_file", {"group_id": group_id, "file": file, "name": name})

    async def delete_group_file(self, group_id: int, file_id: str):
        return await self._post("delete_group_file", {"group_id": group_id, "file_id": file_id})

    async def create_group_file_folder(self, group_id: int, name: str):
        return await self._post("create_group_file_folder", {"group_id": group_id, "name": name})

    async def delete_group_folder(self, group_id: int, folder_id: str):
        return await self._post("delete_group_folder", {"group_id": group_id, "folder_id": folder_id})

    async def get_group_file_url(self, file_id: str):
        return await self._post("get_group_file_url", {"file_id": file_id})

    async def _send_group_notice(self, group_id: int, content: str, image: str):
        return await self._post("_send_group_notice", {"group_id": group_id, "content": content, "image": image})

    async def _get_group_notice(self, group_id: int):
        return await self._post("_get_group_notice", {"group_id": group_id})

    async def get_group_ignore_add_request(self, group_id: int):
        return await self._post("get_group_ignore_add_request", {"group_id": group_id})

    async def send_group_sign(self, group_id: int):
        return await self._post("send_group_sign", {"group_id": group_id})

    def get_login_info(self):
        url = f"{self.http_server}/get_login_info"
        response = requests.get(url, headers=self.headers)
        self.id = int(response.json()["data"]["user_id"])
        self.nickname = response.json()["data"]["nickname"]

    async def get_record(self, file: str, out_format="mp3"):
        return await self._post("get_record", {"file": file, "out_format": out_format})

    async def get_video(self, url: str, path: str):
        async with httpx.AsyncClient(timeout=200) as client:
            response = await client.get(url)
            with open(path, "wb") as file_obj:
                file_obj.write(response.content)
        return path

    async def _post(self, action: str, payload: dict):
        url = f"{self.http_server}/{action}"
        async with httpx.AsyncClient(headers=self.headers, timeout=200) as client:
            response = await client.post(url, json=payload)
            return response.json()

    def _build_message_chain(self, components: Union[str, list[Union[MessageComponent, str]]]):
        if isinstance(components, str):
            components = [Text(components)]
        if not isinstance(components, list):
            components = [components]
        else:
            components = [Text(component) if isinstance(component, str) else component for component in components]
        return MessageChain(components)


__all__ = ["http_mailman"]

