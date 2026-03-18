"""Compatibility exports for legacy NapCat-specific imports."""

from adapters.onebot import NapCatAdapter, NapCatApiClient, OneBotEventFactory, OneBotEventSource, OneBotWebSocketSession

NapCatEventFactory = OneBotEventFactory
NapCatEventSource = OneBotEventSource
NapCatWebSocketSession = OneBotWebSocketSession

__all__ = [
    "NapCatAdapter",
    "NapCatApiClient",
    "NapCatEventFactory",
    "NapCatEventSource",
    "NapCatWebSocketSession",
]
