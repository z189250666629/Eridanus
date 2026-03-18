"""Shared event bus extracted from the legacy WebSocket bot implementation."""

from __future__ import annotations

import asyncio
import time
from typing import Callable, Dict, Type

from core.event.base import EventBase
from core.toolkit.logger import get_logger


class EventBus:
    """Async event bus with optional slow-handler monitoring."""

    def __init__(self, handler_timeout_warning: float = 10.0, enable_monitoring: bool = True) -> None:
        self.handlers: dict[Type[EventBase], set] = {}
        self.handler_timeout_warning = handler_timeout_warning
        self.enable_monitoring = enable_monitoring
        self.logger = get_logger() if enable_monitoring else None
        self._handler_info_cache: Dict[Callable, str] = {}

    def subscribe(self, event: Type[EventBase], handler: Callable) -> None:
        if event not in self.handlers:
            self.handlers[event] = set()
        self.handlers[event].add(handler)

    def on(self, event: Type[EventBase]):
        def decorator(func: Callable):
            self.subscribe(event, func)
            return func

        return decorator

    def set_handler_timeout_warning(self, timeout: float) -> None:
        self.handler_timeout_warning = timeout
        if self.logger:
            self.logger.info_msg(f"Handler超时警告阈值已设置为: {timeout}秒")

    def toggle_monitoring(self, enabled: bool) -> None:
        self.enable_monitoring = enabled
        if enabled and self.logger is None:
            self.logger = get_logger()

    async def _execute_handler_with_monitoring(self, handler: Callable, event_instance: EventBase) -> None:
        start_time = time.perf_counter()

        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_instance)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event_instance)
        except Exception as e:
            if self.logger:
                handler_info = self._get_handler_info_cached(handler)
                self.logger.error(f"Handler执行出错 {handler_info}: {e}", exc_info=True)
        finally:
            execution_time = time.perf_counter() - start_time
            if self.logger and execution_time > self.handler_timeout_warning:
                handler_info = self._get_handler_info_cached(handler)
                self.logger.warning(
                    f"⚠️ Handler执行时间过长: {execution_time:.3f}s (阈值: {self.handler_timeout_warning}s)\n"
                    f"   Handler信息: {handler_info}\n"
                    f"   事件类型: {type(event_instance).__name__}\n"
                    f"   建议检查是否包含阻塞代码"
                )

    def _get_handler_info_cached(self, handler: Callable) -> str:
        if handler in self._handler_info_cache:
            return self._handler_info_cache[handler]

        try:
            func_name = handler.__name__ if hasattr(handler, "__name__") else str(handler)
            if hasattr(handler, "__code__"):
                code = handler.__code__
                info = f"{func_name} at {code.co_filename}:{code.co_firstlineno}"
            elif hasattr(handler, "__call__") and hasattr(handler.__call__, "__code__"):
                code = handler.__call__.__code__
                info = f"{func_name} at {code.co_filename}:{code.co_firstlineno}"
            else:
                info = f"{func_name} (位置信息不可用)"
        except Exception as e:
            info = f"Unknown handler (获取信息失败: {e})"

        self._handler_info_cache[handler] = info
        return info

    async def emit(self, event_instance: EventBase) -> None:
        event_type = type(event_instance)
        handlers = self.handlers.get(event_type)
        if not handlers:
            return

        if self.enable_monitoring:
            for handler in handlers:
                asyncio.create_task(
                    self._execute_handler_with_monitoring(handler, event_instance),
                    name=f"handler-{handler.__name__ if hasattr(handler, '__name__') else 'unknown'}",
                )
            return

        for handler in handlers:
            asyncio.create_task(handler(event_instance))


__all__ = ["EventBus"]


