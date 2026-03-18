"""OneBot implementation-specific outbound compatibility helpers."""

from __future__ import annotations

from typing import Union

from core.message.message_components import At, File, MessageComponent, Music, Node, Poke, Reply, Text


ComponentLike = Union[MessageComponent, str]


def is_lagrange_adapter(adapter_name: str | None) -> bool:
    """Return whether the current OneBot implementation is Lagrange."""
    return (adapter_name or "").strip().lower() == "lagrange"


def normalize_outbound_components(
    components: ComponentLike | list[ComponentLike],
    *,
    adapter_name: str | None,
    quote: bool = False,
    message_id: int | str | None = None,
    bot_id: int | str | None = None,
    bot_name: str | None = None,
) -> tuple[list[ComponentLike], bool]:
    """Normalize outbound components for the target OneBot implementation."""

    normalized = _ensure_component_list(components)
    quote_enabled = quote

    if message_id == 114514:
        quote_enabled = False

    if not is_lagrange_adapter(adapter_name):
        return normalized, quote_enabled

    if quote_enabled and message_id is not None:
        normalized.insert(0, Reply(id=str(message_id)))
        quote_enabled = False

    for index, item in enumerate(normalized):
        normalized[index] = _normalize_lagrange_component(
            item,
            bot_id=bot_id,
            bot_name=bot_name,
        )

    return normalized, quote_enabled


def _ensure_component_list(components: ComponentLike | list[ComponentLike]) -> list[ComponentLike]:
    if isinstance(components, str):
        return [Text(components)]
    if isinstance(components, list):
        return list(components)
    return [components]


def _normalize_lagrange_component(
    component: ComponentLike,
    *,
    bot_id: int | str | None,
    bot_name: str | None,
) -> ComponentLike:
    if isinstance(component, Music):
        component.id = str(component.id)
    elif isinstance(component, At):
        component.qq = str(component.qq)
    elif isinstance(component, Poke):
        component.type = str(component.type)
        component.id = str(component.id)
    elif isinstance(component, File):
        component.file = component.file.replace("file://", "")
    elif isinstance(component, Reply):
        component.id = str(component.id)
    elif isinstance(component, Node):
        if bot_id is not None:
            component.user_id = str(bot_id)
        if bot_name is not None:
            component.nickname = str(bot_name)
    return component


__all__ = [
    "ComponentLike",
    "is_lagrange_adapter",
    "normalize_outbound_components",
]

