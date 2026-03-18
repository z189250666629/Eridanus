"""Shared OneBot raw payload to legacy event conversion."""

from __future__ import annotations

from typing import Any

from core.event.factory import EventFactory


class OneBotEventFactory:
    """Compatibility wrapper around the legacy OneBot event factory."""

    @staticmethod
    def create_event(raw_event: dict[str, Any]) -> Any:
        event_obj = EventFactory.create_event(raw_event)
        if event_obj is None:
            return None

        if not hasattr(event_obj, "raw_event"):
            setattr(event_obj, "raw_event", raw_event)
        if not hasattr(event_obj, "platform_data"):
            setattr(event_obj, "platform_data", raw_event)
        return event_obj


__all__ = ["OneBotEventFactory"]

