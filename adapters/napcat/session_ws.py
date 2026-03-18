"""NapCat WebSocket session wrapper."""

from __future__ import annotations

from adapters.onebot.session_ws import OneBotWebSocketSession


class NapCatWebSocketSession(OneBotWebSocketSession):
    """NapCat-flavored wrapper around the shared OneBot WebSocket session."""


__all__ = ["NapCatWebSocketSession"]
