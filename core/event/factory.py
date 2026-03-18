from typing import Any, Dict, Optional, Type

from core.event.base import EventBase
from core.event.events import (
    FriendAddNoticeEvent,
    FriendRecallNoticeEvent,
    FriendRequestEvent,
    GroupAdminNoticeEvent,
    GroupBanNoticeEvent,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
    GroupMessageEvent,
    GroupRecallNoticeEvent,
    GroupRequestEvent,
    GroupUploadNoticeEvent,
    HeartbeatMetaEvent,
    HonorNotifyEvent,
    LifecycleMetaEvent,
    LuckyKingNotifyEvent,
    PokeNotifyEvent,
    PrivateMessageEvent,
    ProfileLikeEvent,
    startUpMetaEvent,
)


class EventFactory:
    """Factory for converting raw OneBot payloads into event models."""

    event_mapping: Dict[str, Type[EventBase]] = {
        "request": {
            "friend": FriendRequestEvent,
            "group": GroupRequestEvent,
        },
        "message": {
            "private": PrivateMessageEvent,
            "group": GroupMessageEvent,
        },
        "notice": {
            "group_upload": GroupUploadNoticeEvent,
            "group_admin": GroupAdminNoticeEvent,
            "group_decrease": GroupDecreaseNoticeEvent,
            "group_increase": GroupIncreaseNoticeEvent,
            "group_ban": GroupBanNoticeEvent,
            "friend_add": FriendAddNoticeEvent,
            "group_recall": GroupRecallNoticeEvent,
            "friend_recall": FriendRecallNoticeEvent,
            "notify": {
                "lucky_king": LuckyKingNotifyEvent,
                "poke": PokeNotifyEvent,
                "profile_like": ProfileLikeEvent,
                "honor": HonorNotifyEvent,
            },
        },
        "meta_event": {
            "lifecycle": LifecycleMetaEvent,
            "heartbeat": HeartbeatMetaEvent,
            "startUp": startUpMetaEvent,
        },
    }

    @staticmethod
    def create_event(data: Dict[str, Any]) -> Optional[EventBase]:
        post_type = data.get("post_type")
        if not post_type:
            print(f"post_type未匹配，未知事件类型: {data}")
            return None

        sub_mapping = EventFactory.event_mapping.get(post_type)
        if not sub_mapping:
            return None

        sub_type = (
            data.get("message_type")
            or data.get("notice_type")
            or data.get("request_type")
            or data.get("meta_event_type")
        )
        if sub_type == "notify":
            sub_type = data.get("sub_type")
            event_class = sub_mapping.get("notify").get(sub_type)
        else:
            event_class = sub_mapping.get(sub_type)

        if not event_class:
            print(f"子类型未匹配，未知事件: {data}")
            return None

        return event_class(**data)


__all__ = ["EventFactory"]
