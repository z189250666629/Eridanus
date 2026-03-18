"""Compatibility wrapper for the shared OneBot event source."""

from adapters.onebot.event_source import OneBotEventSource as NapCatEventSource


__all__ = ["NapCatEventSource"]
