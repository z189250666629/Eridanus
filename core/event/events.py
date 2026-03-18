# pyright: reportIncompatibleVariableOverride=false
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict
from pydantic.v1 import validator

from core.message.cq_parser import (
    parse_message_2processed_message,
    parse_message_with_cq_codes_to_list,
)
from core.event.base import EventBase
from core.message.message_chain import MessageChain


class Sender(BaseModel):
    user_id: Optional[int] = None
    nickname: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[int] = None
    card: Optional[str] = None
    area: Optional[str] = None
    level: Optional[str] = None
    role: Optional[str] = None
    title: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class Reply(BaseModel):
    time: int
    message_type: str
    message_id: int
    real_id: int
    sender: Sender
    message: List[Dict[str, Any]]

    model_config = ConfigDict(extra="allow")

    @validator("message", pre=True, always=True)
    def ensure_message_chain(cls, value):
        return MessageChain(value)


class Anonymous(BaseModel):
    id: int
    name: str
    flag: str

    model_config = ConfigDict(extra="allow")


class File(BaseModel):
    id: str
    name: str
    size: int
    busid: int

    model_config = ConfigDict(extra="allow")


class Status(BaseModel):
    online: bool
    good: bool

    model_config = ConfigDict(extra="allow")


class LifecycleMetaEvent(BaseModel):
    time: int
    sender: int
    post_type: str
    meta_event_type: str
    sub_type: str


class MessageEvent(BaseModel):
    post_type: Literal["message"]
    sub_type: str
    user_id: int
    message_type: str
    message_id: int
    message: List[Dict[str, Any]]
    original_message: Optional[list] = None
    _raw_message: str
    font: int
    sender: Sender
    to_me: bool = False
    reply: Optional[Reply] = None

    processed_message: List[Dict[str, Union[str, Dict]]] = []
    message_chain: MessageChain = []
    pure_text: str = ""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    @property
    def raw_message(self):
        return self._raw_message

    @raw_message.setter
    def raw_message(self, value: str):
        self._raw_message = value
        if value == "":
            self.processed_message = parse_message_2processed_message(self.message)
        else:
            self.processed_message = parse_message_with_cq_codes_to_list(value)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, "raw_message"):
            if self.raw_message == "":
                self.processed_message = parse_message_2processed_message(self.message)
            else:
                self.processed_message = parse_message_with_cq_codes_to_list(self.raw_message)
        self.message_chain = MessageChain(self.message)
        self.pure_text = self.message_chain.fetch_text()

    def get(self, message_type: str):
        result = [msg[message_type] for msg in self.processed_message if message_type in msg]
        if result and message_type == "image" and "url" not in result[0]:
            result[0]["url"] = result[0]["file"]
        return result if result else None


class PrivateMessageEvent(MessageEvent):
    message_type: Literal["private"]


class GroupMessageEvent(MessageEvent):
    message_type: Literal["group"]
    group_id: int
    anonymous: Optional[Anonymous] = None


class NoticeEvent(EventBase):
    post_type: Literal["notice"]
    notice_type: str


class GroupUploadNoticeEvent(NoticeEvent):
    notice_type: Literal["group_upload"]
    user_id: int
    group_id: int
    file: File


class GroupAdminNoticeEvent(NoticeEvent):
    notice_type: Literal["group_admin"]
    sub_type: str
    user_id: int
    group_id: int


class GroupDecreaseNoticeEvent(NoticeEvent):
    notice_type: Literal["group_decrease"]
    sub_type: str
    user_id: int
    group_id: int
    operator_id: int


class GroupIncreaseNoticeEvent(NoticeEvent):
    notice_type: Literal["group_increase"]
    sub_type: str
    user_id: int
    group_id: int
    operator_id: int


class GroupBanNoticeEvent(NoticeEvent):
    notice_type: Literal["group_ban"]
    sub_type: str
    user_id: int
    group_id: int
    operator_id: int
    duration: int


class FriendAddNoticeEvent(NoticeEvent):
    notice_type: Literal["friend_add"]
    user_id: int


class GroupRecallNoticeEvent(NoticeEvent):
    notice_type: Literal["group_recall"]
    user_id: int
    group_id: int
    operator_id: int
    message_id: int


class FriendRecallNoticeEvent(NoticeEvent):
    notice_type: Literal["friend_recall"]
    user_id: int
    message_id: int


class NotifyEvent(NoticeEvent):
    notice_type: Literal["notify"]
    sub_type: str
    user_id: int = None
    group_id: int = None


class PokeNotifyEvent(NotifyEvent):
    sub_type: Literal["poke"]
    target_id: int
    group_id: Optional[int] = None
    raw_info: list = None


class LuckyKingNotifyEvent(NotifyEvent):
    sub_type: Literal["lucky_king"]
    target_id: int


class ProfileLikeEvent(NotifyEvent):
    sub_type: Literal["profile_like"]
    operator_id: int
    operator_nick: str
    times: int


class HonorNotifyEvent(NotifyEvent):
    sub_type: Literal["honor"]
    honor_type: str


class RequestEvent(EventBase):
    post_type: Literal["request"]
    request_type: str


class FriendRequestEvent(RequestEvent):
    request_type: Literal["friend"]
    user_id: int
    flag: str
    comment: Optional[str] = None


class GroupRequestEvent(RequestEvent):
    request_type: Literal["group"]
    sub_type: str
    group_id: int
    user_id: int
    flag: str
    comment: Optional[str] = None


class MetaEvent(EventBase):
    post_type: Literal["meta_event"]
    meta_event_type: str


class LifecycleMetaEvent(MetaEvent):
    meta_event_type: Literal["lifecycle"]
    sub_type: str


class startUpMetaEvent(MetaEvent):
    meta_event_type: Literal["startUp"]


class HeartbeatMetaEvent(MetaEvent):
    meta_event_type: Literal["heartbeat"]
    status: Status
    interval: int


__all__ = [
    "MessageEvent",
    "PrivateMessageEvent",
    "GroupMessageEvent",
    "NoticeEvent",
    "GroupUploadNoticeEvent",
    "GroupAdminNoticeEvent",
    "GroupDecreaseNoticeEvent",
    "GroupIncreaseNoticeEvent",
    "GroupBanNoticeEvent",
    "FriendAddNoticeEvent",
    "GroupRecallNoticeEvent",
    "FriendRecallNoticeEvent",
    "NotifyEvent",
    "PokeNotifyEvent",
    "ProfileLikeEvent",
    "LuckyKingNotifyEvent",
    "HonorNotifyEvent",
    "RequestEvent",
    "FriendRequestEvent",
    "GroupRequestEvent",
    "MetaEvent",
    "LifecycleMetaEvent",
    "HeartbeatMetaEvent",
    "startUpMetaEvent",
]

