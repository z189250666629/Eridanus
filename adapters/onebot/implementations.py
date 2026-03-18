"""OneBot implementation-specific adapters and API clients."""

from __future__ import annotations

from typing import Any

from .adapter import OneBotAdapter
from .api_client import OneBotApiClient
from .capabilities import normalize_outbound_components
from .event_source import OneBotEventSource
from .session_ws import OneBotWebSocketSession


class NapCatApiClient(OneBotApiClient):
    """NapCat-specific API client extending shared OneBot behaviors."""

    async def get_ai_characters(self) -> dict[str, Any]:
        return await self.call_api("get_ai_characters", {"group_id": 0, "chat_type": 1})

    async def get_ai_record(self, group_id: int, character: str, text: str) -> dict[str, Any]:
        return await self.call_api(
            "get_ai_record",
            {"group_id": group_id, "character": character, "text": text},
        )


class LagrangeApiClient(OneBotApiClient):
    """Lagrange-specific API client built on top of shared OneBot behaviors."""

    async def fetch_custom_face(self) -> dict[str, Any]:
        return await self.call_api("fetch_custom_face", {})

    async def get_friend_msg_history(
        self,
        user_id: int,
        message_id: int,
        count: int = 20,
    ) -> dict[str, Any]:
        return await self.call_api(
            "get_friend_msg_history",
            {"user_id": user_id, "message_id": message_id, "count": count},
        )

    async def get_group_msg_history(
        self,
        group_id: int,
        message_id: int,
        count: int = 20,
    ) -> dict[str, Any]:
        return await self.call_api(
            "get_group_msg_history",
            {"group_id": group_id, "message_id": message_id, "count": count},
        )

    async def get_group_files_by_folder(self, group_id: int, folder_id: str) -> dict[str, Any]:
        return await self.call_api(
            "get_group_files_by_folder",
            {"group_id": group_id, "folder_id": folder_id},
        )

    async def upload_group_file(
        self,
        group_id: int,
        file: str,
        name: str | None = None,
        folder: str | None = None,
    ) -> dict[str, Any]:
        params = {"group_id": group_id, "file": file, "name": name}
        if folder is not None:
            params["folder"] = folder
        return await self.call_api("upload_group_file", params)

    async def get_group_file_url(self, group_id: int, file_id: str, busid: int) -> dict[str, Any]:
        return await self.call_api(
            "get_group_file_url",
            {"group_id": group_id, "file_id": file_id, "busid": busid},
        )


class NapCatAdapter(OneBotAdapter):
    """OneBot adapter with NapCat-specific API extensions."""

    def __init__(
        self,
        uri: str,
        *,
        logger: Any,
        event_source: OneBotEventSource | None = None,
        api_client: NapCatApiClient | None = None,
        session: OneBotWebSocketSession | None = None,
    ) -> None:
        shared_session = session or OneBotWebSocketSession(uri, logger=logger)
        super().__init__(
            uri,
            logger=logger,
            session=shared_session,
            api_client=api_client
            or NapCatApiClient(
                shared_session,
                logger=logger,
                readiness_checker=lambda: shared_session.websocket is not None,
            ),
            event_source=event_source,
        )


class LagrangeAdapter(OneBotAdapter):
    """OneBot adapter with Lagrange-specific outbound compatibility."""

    def __init__(
        self,
        uri: str,
        *,
        logger: Any,
        event_source: OneBotEventSource | None = None,
        api_client: LagrangeApiClient | None = None,
        session: OneBotWebSocketSession | None = None,
        bot_name: str | None = None,
    ) -> None:
        shared_session = session or OneBotWebSocketSession(uri, logger=logger)
        super().__init__(
            uri,
            logger=logger,
            session=shared_session,
            api_client=api_client
            or LagrangeApiClient(
                shared_session,
                logger=logger,
                readiness_checker=lambda: shared_session.websocket is not None,
            ),
            event_source=event_source,
        )
        self.bot_name = bot_name

    async def send(self, event: Any, components: Any, quote: bool = False) -> Any:
        components, quote = normalize_outbound_components(
            components,
            adapter_name="Lagrange",
            quote=quote,
            message_id=getattr(event, "message_id", None),
            bot_id=self.id,
            bot_name=self.bot_name,
        )
        return await super().send(event, components, quote)


__all__ = [
    "LagrangeAdapter",
    "LagrangeApiClient",
    "NapCatAdapter",
    "NapCatApiClient",
]
