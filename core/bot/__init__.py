"""Bot runtime layer with lazy exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "Bot",
    "DualBotManager",
    "ExtendBot",
    "EventBus",
    "FuncMap",
    "PluginInterface",
    "PluginManager",
    "PluginMeta",
    "PluginRuntimeContext",
    "SkillDocument",
    "bot_info_collect",
    "build_tool_fixed_params",
    "build_tool_map",
    "filter_tools_by_config",
    "get_tool_declarations",
    "load_main_functions",
    "parse_plugin_skill",
    "parse_skill_file",
    "scan_plugins",
]


def __getattr__(name: str) -> Any:
    if name == "Bot":
        return import_module(".bot", __name__).Bot
    if name == "DualBotManager":
        return import_module(".dual_bot_manager", __name__).DualBotManager
    if name == "ExtendBot":
        return import_module(".extend_bot", __name__).ExtendBot
    if name == "EventBus":
        return import_module(".event_bus", __name__).EventBus
    if name == "FuncMap":
        return import_module(".func_map", __name__).FuncMap
    if name in {
        "build_tool_fixed_params",
        "build_tool_map",
        "filter_tools_by_config",
        "get_tool_declarations",
        "scan_plugins",
    }:
        module = import_module(".func_map_loader", __name__)
        return getattr(module, name)
    if name == "load_main_functions":
        return import_module(".main_func_detector", __name__).load_main_functions
    if name == "bot_info_collect":
        return import_module(".bot_info", __name__).bot_info_collect
    if name in {"PluginInterface", "PluginManager", "PluginMeta", "PluginRuntimeContext"}:
        module = import_module(".plugin_manager", __name__)
        return getattr(module, name)
    if name in {"SkillDocument", "parse_plugin_skill", "parse_skill_file"}:
        module = import_module(".skill_parser", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
