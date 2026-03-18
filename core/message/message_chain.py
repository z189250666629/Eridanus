from typing import Any, Dict, List, Type, Union

from core.message.message_components import (
    At,
    Anonymous,
    Contact,
    Contact_group,
    Contact_user,
    Dice,
    Face,
    File,
    Forward,
    Image,
    Json,
    Location,
    Markdown,
    MessageComponent,
    Mface,
    Music,
    Node,
    Poke,
    Record,
    Reply,
    Rps,
    Shake,
    Share,
    Text,
    Video,
    Xml,
)


class MessageChain(list):
    """Message chain that parses raw dict payloads into typed components."""

    _type_map: Dict[str, Type[MessageComponent]] = {
        "text": Text,
        "face": Face,
        "image": Image,
        "record": Record,
        "video": Video,
        "at": At,
        "rps": Rps,
        "dice": Dice,
        "shake": Shake,
        "poke": Poke,
        "anonymous": Anonymous,
        "share": Share,
        "contact": Contact,
        "location": Location,
        "music": Music,
        "reply": Reply,
        "forward": Forward,
        "node": Node,
        "xml": Xml,
        "json": Json,
        "contact_user": Contact_user,
        "contact_group": Contact_group,
        "mface": Mface,
        "file": File,
        "markdown": Markdown,
    }

    def __init__(self, messages: List[Union[MessageComponent, Dict[str, Any], str]]):
        if self._is_all_components(messages):
            super().__init__(messages)
        else:
            super().__init__(self._parse_messages(messages))

    def _is_all_components(self, messages: List[Any]) -> bool:
        return all(isinstance(item, MessageComponent) for item in messages)

    @classmethod
    def _parse_messages(
        cls, messages: List[Union[MessageComponent, Dict[str, Any], str]]
    ) -> List[MessageComponent]:
        parsed_messages = []

        for msg in messages:
            if isinstance(msg, MessageComponent):
                parsed_messages.append(msg)
            elif isinstance(msg, str):
                parsed_messages.append(Text(msg))
            elif isinstance(msg, dict):
                msg_type = msg.get("type")
                msg_data = msg.get("data", {})

                component_class = cls._type_map.get(msg_type)
                if component_class:
                    try:
                        parsed_messages.append(component_class(**msg_data))
                    except Exception as exc:
                        print(f"解析消息失败: {msg_type}, 原始数据: {msg_data}, 错误信息: {exc}")
                else:
                    print(f"未知消息类型: {msg_type}, 原始数据: {msg}")
                    parsed_messages.append(Text(str(msg)))
            else:
                raise TypeError(f"无效的消息格式: {msg}")

        return parsed_messages

    def to_dict(self) -> list[dict[str, Any]]:
        return [x.to_dict() for x in self]

    def has(self, component_type: Type[MessageComponent]) -> bool:
        return any(isinstance(component, component_type) for component in self)

    def __contains__(self, obj: Any) -> bool:
        return self.has(obj)

    def get(self, component_type: Type[MessageComponent]) -> List[MessageComponent]:
        return [component for component in self if isinstance(component, component_type)]

    def fetch_text(self) -> str:
        if self.has(Text) and not self.has(At):
            return self.get(Text)[0].text.strip()
        return ""


__all__ = ["MessageChain"]
