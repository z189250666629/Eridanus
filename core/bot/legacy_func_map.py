"""Legacy func_map compatibility layer hosted under core.bot."""

from __future__ import annotations

import inspect

from core.toolkit.logger import get_logger

from .func_map_loader import build_tool_map, dynamic_imports as loader_dynamic_imports, scan_plugins

logger = get_logger("legacy_func_map")
dynamic_imports = {}
loaded_functions = {}


def refresh_loaded_functions():
    """Refresh legacy tool maps from the new plugin registry loader."""
    global loaded_functions

    scan_plugins()
    dynamic_imports.clear()
    dynamic_imports.update(loader_dynamic_imports)
    loaded_functions = build_tool_map()
    return loaded_functions


try:
    refresh_loaded_functions()
except Exception as exc:
    logger.error(f"❌ 初始化 legacy_func_map 失败: {exc}", exc_info=True)


async def call_quit_chat(bot, event, config):
    return False


async def call_func(bot, event, config, func_name, params):
    """
    Dynamically call an already registered async tool.

    Keeps the legacy signature used by historical callers.
    """
    print(f"Calling function '{func_name}' with parameters: {params}")

    func = loaded_functions.get(func_name)
    if func is None:
        raise ValueError(f"Function '{func_name}' not found in loaded_functions.")
    if not callable(func):
        raise TypeError(f"'{func_name}' is not callable.")
    if not inspect.iscoroutinefunction(func):
        raise TypeError(f"'{func_name}' is not an async function.")

    return await func(bot, event, config, **params)


__all__ = [
    "call_func",
    "call_quit_chat",
    "dynamic_imports",
    "loaded_functions",
    "refresh_loaded_functions",
]
