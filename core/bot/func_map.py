"""Explicit function registry for plugin tool declarations."""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.toolkit.logger import get_logger

if TYPE_CHECKING:
    from .skill_parser import SkillDocument


NETWORK_SEARCH_FUNCTIONS = {"search_net", "read_html"}
OFFICIAL_SEARCH_FUNCTIONS = {"search_with_official_api"}


@dataclass(slots=True)
class PluginToolRegistration:
    """Tool metadata registered by one plugin."""

    dynamic_imports: dict[str, list[str] | list[Any]] = field(default_factory=dict)
    function_declarations: list[dict[str, Any]] = field(default_factory=list)
    skill_documents: list["SkillDocument"] = field(default_factory=list)


class FuncMap:
    """Plugin-scoped function registry."""

    def __init__(self) -> None:
        self.logger = get_logger("FuncMap")
        self._plugins: dict[str, PluginToolRegistration] = {}

    def register(
        self,
        plugin_name: str,
        *,
        dynamic_imports: dict[str, list[str] | list[Any]] | None = None,
        function_declarations: list[dict[str, Any]] | None = None,
        skill_documents: list["SkillDocument"] | None = None,
    ) -> None:
        self._plugins[plugin_name] = PluginToolRegistration(
            dynamic_imports=dict(dynamic_imports or {}),
            function_declarations=list(function_declarations or []),
            skill_documents=list(skill_documents or []),
        )

    def register_from_package(
        self,
        plugin_name: str,
        package_module: Any,
        *,
        skill_documents: list["SkillDocument"] | None = None,
    ) -> None:
        self.register(
            plugin_name,
            dynamic_imports=getattr(package_module, "dynamic_imports", {}),
            function_declarations=getattr(package_module, "function_declarations", []),
            skill_documents=skill_documents,
        )

    def unregister(self, plugin_name: str) -> None:
        self._plugins.pop(plugin_name, None)

    def build_tool_map(self) -> dict[str, Any]:
        tools: dict[str, Any] = {}

        for plugin_name, registration in self._plugins.items():
            for module_name, imports in registration.dynamic_imports.items():
                try:
                    module = importlib.import_module(module_name)
                except Exception as exc:
                    self.logger.error(f"❌ 无法导入模块 {module_name}: {exc}", exc_info=True)
                    continue

                for imported in imports:
                    func_name = imported if isinstance(imported, str) else getattr(imported, "__name__", None)
                    if func_name is None:
                        self.logger.warning(f"⚠️ 插件 {plugin_name} 的 dynamic_imports 含无效项: {imported}")
                        continue

                    func = getattr(module, func_name, None) if isinstance(imported, str) else imported
                    if callable(func):
                        tools[func_name] = func
                    else:
                        self.logger.warning(f"⚠️ {module_name}.{func_name} 不可调用")

        return tools

    def get_declarations(self, config: Any | None = None) -> list[dict[str, Any]]:
        declarations: list[dict[str, Any]] = []

        for registration in self._plugins.values():
            declarations.extend(registration.function_declarations)

        if config is None:
            return declarations

        try:
            google_search_enabled = config.ai_llm.config["llm"].get("google_search", False)
            url_context_enabled = config.ai_llm.config["llm"].get("url_context", False)
        except Exception as exc:
            self.logger.warning(f"检查搜索配置时出错: {exc}")
            return declarations

        if google_search_enabled or url_context_enabled:
            return [
                declaration
                for declaration in declarations
                if declaration.get("name") not in NETWORK_SEARCH_FUNCTIONS
            ]

        return [
            declaration
            for declaration in declarations
            if declaration.get("name") not in OFFICIAL_SEARCH_FUNCTIONS
        ]

    def get_skill_documents(self, plugin_name: str | None = None) -> list["SkillDocument"]:
        if plugin_name is not None:
            registration = self._plugins.get(plugin_name)
            if registration is None:
                return []
            return list(registration.skill_documents)

        documents: list["SkillDocument"] = []
        for registration in self._plugins.values():
            documents.extend(registration.skill_documents)
        return documents

    def filter_tools_by_config(self, tools: dict[str, Any], config: Any | None = None) -> dict[str, Any]:
        if config is None:
            return tools

        try:
            google_search_enabled = config.ai_llm.config["llm"].get("google_search", False)
            url_context_enabled = config.ai_llm.config["llm"].get("url_context", False)
        except Exception as exc:
            self.logger.warning(f"过滤工具时检查配置出错: {exc}")
            return tools

        blocked = NETWORK_SEARCH_FUNCTIONS if (google_search_enabled or url_context_enabled) else OFFICIAL_SEARCH_FUNCTIONS
        return {name: func for name, func in tools.items() if name not in blocked}

    async def call(
        self,
        *,
        bot: Any,
        event: Any,
        config: Any,
        func_name: str,
        params: dict[str, Any],
    ) -> Any:
        tools = self.build_tool_map()
        func = tools.get(func_name)
        if func is None:
            raise ValueError(f"Function '{func_name}' not found in FuncMap.")
        if not callable(func):
            raise TypeError(f"'{func_name}' is not callable.")
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f"'{func_name}' is not an async function.")
        return await func(bot, event, config, **params)


__all__ = ["FuncMap", "OFFICIAL_SEARCH_FUNCTIONS", "NETWORK_SEARCH_FUNCTIONS", "PluginToolRegistration"]

