"""Shared OneBot transport/client building blocks."""

from .adapter import OneBotAdapter
from .api_client import OneBotApiClient
from .capabilities import ComponentLike, is_lagrange_adapter, normalize_outbound_components
from .event_factory import OneBotEventFactory
from .event_source import OneBotEventSource
from .http_adapter import HTTPBot
from .http_mailman import http_mailman
from .implementations import LagrangeAdapter, LagrangeApiClient, NapCatAdapter, NapCatApiClient
from .session_ws import OneBotWebSocketSession
from .websocket_bot import WebSocketBot

__all__ = [
    "ComponentLike",
    "HTTPBot",
    "LagrangeAdapter",
    "LagrangeApiClient",
    "NapCatAdapter",
    "NapCatApiClient",
    "OneBotAdapter",
    "OneBotApiClient",
    "OneBotEventFactory",
    "OneBotEventSource",
    "OneBotWebSocketSession",
    "WebSocketBot",
    "http_mailman",
    "is_lagrange_adapter",
    "normalize_outbound_components",
]
