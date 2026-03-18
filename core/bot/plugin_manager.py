"""Composable plugin manager without bot monkey-patching."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.config import PLUGINS_DIR, PLUGINS_MODULE_PREFIX
from core.toolkit.logger import get_logger
from core.services import get_service_registry
from .skill_parser import parse_plugin_skill

if TYPE_CHECKING:
    from .skill_parser import SkillDocument


@dataclass(slots=True)
class PluginMeta:
    """Plugin metadata loaded from the plugin package."""

    name: str
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    module_name: str = ""
    path: str = ""


class PluginInterface:
    """Optional class-style plugin contract for new plugins."""

    meta: PluginMeta | None = None

    async def setup(self, bot: Any, config: Any, context: "PluginRuntimeContext") -> None:
        """Initialize the plugin."""

    async def teardown(self) -> None:
        """Release plugin resources."""


@dataclass(slots=True)
class LoadedPlugin:
    """Runtime bookkeeping for a loaded plugin."""

    meta: PluginMeta
    context: "PluginRuntimeContext"
    modules: list[str] = field(default_factory=list)
    function_entries: list[Any] = field(default_factory=list)
    instance_entries: list[PluginInterface] = field(default_factory=list)
    skill_document: "SkillDocument | None" = None
    package_module: Any | None = None


class PluginRuntimeContext:
    """Per-plugin bot proxy used to record registered handlers."""

    def __init__(self, bot: Any, plugin_name: str) -> None:
        self._bot = bot
        self.plugin_name = plugin_name
        self.registered_handlers: list[tuple[Any, Any]] = []

    def on(self, event_type: Any):
        """Delegate handler registration while recording ownership."""

        def decorator(func: Any):
            result = self._bot.on(event_type)(func)
            self.registered_handlers.append((event_type, func))
            return result

        return decorator

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bot, name)


class PluginManager:
    """Load plugins with explicit lifecycle management."""

    def __init__(
        self,
        bot: Any,
        config: Any,
        *,
        plugins_dir: str = PLUGINS_DIR,
        plugins_module_prefix: str = PLUGINS_MODULE_PREFIX,
        func_map: Any | None = None,
        enable_file_watcher: bool = True,
        reload_debounce_seconds: float = 0.5,
    ) -> None:
        self.bot = bot
        self.config = config
        self.plugins_dir = Path(plugins_dir).resolve()
        self.plugins_module_prefix = plugins_module_prefix
        self.func_map = func_map
        self.enable_file_watcher = enable_file_watcher
        self.reload_debounce_seconds = reload_debounce_seconds
        self.logger = get_logger("CorePluginManager")
        self.loaded_plugins: dict[str, LoadedPlugin] = {}
        self.service_registry = get_service_registry()
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._observer: Any | None = None
        self._plugin_mod_times: dict[str, float] = {}
        self._pending_sync_tasks: dict[str, asyncio.Task[None]] = {}

    async def start(self) -> None:
        self._event_loop = asyncio.get_running_loop()
        await self.load_all_plugins()
        self.start_file_watcher()

    async def stop(self) -> None:
        self.stop_file_watcher()
        for plugin_name in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_name)

    async def load_all_plugins(self) -> None:
        for plugin_dir in sorted(self.plugins_dir.iterdir(), key=lambda item: item.name):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            if not (plugin_dir / "__init__.py").exists():
                continue
            await self.load_plugin(plugin_dir.name)

    async def load_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self.loaded_plugins:
            self.logger.warning(f"插件 {plugin_name} 已加载，跳过重复加载")
            return True

        plugin_dir = self.plugins_dir / plugin_name
        if not plugin_dir.exists():
            self.logger.error(f"插件目录不存在: {plugin_dir}")
            return False

        package_name = self._plugin_module_name(plugin_name)

        try:
            package_module = importlib.import_module(package_name)
            meta = self._load_plugin_meta(plugin_name, plugin_dir, package_module)
            context = PluginRuntimeContext(self.bot, plugin_name)
            skill_document = parse_plugin_skill(plugin_dir)
            loaded_plugin = LoadedPlugin(
                meta=meta,
                context=context,
                skill_document=skill_document,
                package_module=package_module,
            )

            if self.func_map is not None and hasattr(self.func_map, "register_from_package"):
                self.func_map.register_from_package(
                    plugin_name,
                    package_module,
                    skill_documents=[skill_document] if skill_document is not None else [],
                )

            await self._register_plugin_services(package_module, loaded_plugin)

            modules = self._load_plugin_modules(plugin_name)
            loaded_plugin.modules = [module.__name__ for module in modules]

            for module in modules:
                main_func = getattr(module, "main", None)
                if callable(main_func):
                    await self._invoke_callable(main_func, context)
                    loaded_plugin.function_entries.append(main_func)

            for plugin_class in self._discover_plugin_classes(modules):
                instance = plugin_class()
                await self._invoke_plugin_instance(instance, context)
                loaded_plugin.instance_entries.append(instance)

            self.loaded_plugins[plugin_name] = loaded_plugin
            self.logger.info(
                f"插件 {plugin_name} 加载完成: {len(loaded_plugin.function_entries)} 个函数入口, "
                f"{len(loaded_plugin.instance_entries)} 个类式入口"
            )
            return True
        except Exception as exc:
            self.logger.error(f"插件 {plugin_name} 加载失败: {exc}", exc_info=True)
            if self.func_map is not None and hasattr(self.func_map, "unregister"):
                self.func_map.unregister(plugin_name)
            self.service_registry.unregister_by_provider(plugin_name)
            self._clear_plugin_modules_from_cache(plugin_name)
            return False

    async def unload_plugin(self, plugin_name: str) -> None:
        loaded_plugin = self.loaded_plugins.pop(plugin_name, None)
        if loaded_plugin is None:
            return

        for instance in reversed(loaded_plugin.instance_entries):
            teardown = getattr(instance, "teardown", None) or getattr(instance, "stop", None)
            if teardown is None:
                continue
            await self._invoke_with_supported_kwargs(
                teardown,
                bot=loaded_plugin.context,
                config=self.config,
                context=loaded_plugin.context,
            )

        await self._unregister_plugin_services(loaded_plugin)
        self._unregister_handlers(loaded_plugin.context)
        if self.func_map is not None and hasattr(self.func_map, "unregister"):
            self.func_map.unregister(plugin_name)
        self._clear_plugin_modules_from_cache(plugin_name)
        self.logger.info(
            f"插件 {plugin_name} 已卸载，清理 {len(loaded_plugin.context.registered_handlers)} 个事件处理器"
        )

    async def reload_plugin(self, plugin_name: str) -> bool:
        await self.unload_plugin(plugin_name)
        return await self.load_plugin(plugin_name)

    async def reload_all_plugins(self) -> None:
        for plugin_name in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_name)
        await self.load_all_plugins()

    def start_file_watcher(self) -> None:
        """Watch plugin files and sync plugin state when they change."""
        if not self.enable_file_watcher:
            return
        if self._observer is not None:
            return
        if not self.plugins_dir.exists():
            self.logger.warning(f"插件目录不存在，跳过文件监控: {self.plugins_dir}")
            return

        try:
            from watchdog.events import FileSystemEvent, FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            self.logger.warning("watchdog 未安装，已跳过插件文件监控")
            return

        plugin_manager = self

        class PluginFileHandler(FileSystemEventHandler):
            def on_modified(self, event: FileSystemEvent) -> None:
                self._handle_event(event)

            def on_created(self, event: FileSystemEvent) -> None:
                self._handle_event(event)

            def on_deleted(self, event: FileSystemEvent) -> None:
                self._handle_event(event)

            def on_moved(self, event: FileSystemEvent) -> None:
                self._handle_event(event)

            def _handle_event(self, event: FileSystemEvent) -> None:
                if event.is_directory:
                    return

                candidate_paths = [Path(event.src_path)]
                dest_path = getattr(event, "dest_path", None)
                if dest_path:
                    candidate_paths.append(Path(dest_path))

                for file_path in candidate_paths:
                    if not plugin_manager._is_plugin_related_file(file_path):
                        continue
                    plugin_name = plugin_manager._plugin_name_from_path(file_path)
                    if not plugin_name:
                        continue
                    plugin_manager._schedule_plugin_sync(plugin_name, file_path.name)
                    break

        self._observer = Observer()
        self._observer.schedule(PluginFileHandler(), str(self.plugins_dir), recursive=True)
        self._observer.start()
        self.logger.info("插件文件监控已启动")

    def stop_file_watcher(self) -> None:
        observer = self._observer
        if observer is None:
            return

        observer.stop()
        observer.join()
        self._observer = None
        self.logger.info("插件文件监控已停止")

    def get_loaded_plugins(self) -> list[str]:
        return list(self.loaded_plugins.keys())

    async def get_plugin_status(self) -> dict[str, dict[str, Any]]:
        status: dict[str, dict[str, Any]] = {}

        for plugin_dir in sorted(self.plugins_dir.iterdir(), key=lambda item: item.name):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            plugin_name = plugin_dir.name
            loaded = self.loaded_plugins.get(plugin_name)
            status[plugin_name] = {
                "loaded": loaded is not None,
                "path": str(plugin_dir),
                "description": loaded.meta.description if loaded else "",
                "dependencies": loaded.meta.dependencies if loaded else [],
                "event_handlers_count": len(loaded.context.registered_handlers) if loaded else 0,
                "has_skill": loaded.skill_document is not None if loaded else (plugin_dir / "skill.md").exists(),
                "skill_title": loaded.skill_document.title if loaded and loaded.skill_document else "",
                "skill_path": loaded.skill_document.path if loaded and loaded.skill_document else "",
            }

        return status

    def _plugin_module_name(self, plugin_name: str) -> str:
        return f"{self.plugins_module_prefix}.{plugin_name}"

    def _plugin_module_prefixes(self, plugin_name: str) -> list[str]:
        prefixes = [self._plugin_module_name(plugin_name)]
        for namespace in ("run", "plugins"):
            alias_prefix = f"{namespace}.{plugin_name}"
            if alias_prefix not in prefixes:
                prefixes.append(alias_prefix)
        return prefixes

    async def _register_plugin_services(self, package_module: Any, loaded_plugin: LoadedPlugin) -> None:
        register_hook = getattr(package_module, "register_services", None)
        if not callable(register_hook):
            return

        await self._invoke_with_supported_kwargs(
            register_hook,
            registry=self.service_registry,
            provider=loaded_plugin.meta.name,
            bot=loaded_plugin.context,
            config=self.config,
            context=loaded_plugin.context,
            plugin_manager=self,
        )

    async def _unregister_plugin_services(self, loaded_plugin: LoadedPlugin) -> None:
        package_module = loaded_plugin.package_module
        unregister_hook = getattr(package_module, "unregister_services", None) if package_module else None
        if callable(unregister_hook):
            await self._invoke_with_supported_kwargs(
                unregister_hook,
                registry=self.service_registry,
                provider=loaded_plugin.meta.name,
                bot=loaded_plugin.context,
                config=self.config,
                context=loaded_plugin.context,
                plugin_manager=self,
            )

        self.service_registry.unregister_by_provider(loaded_plugin.meta.name)

    def _is_plugin_related_file(self, file_path: Path) -> bool:
        if file_path.name == "__pycache__":
            return False
        if file_path.suffix.lower() not in {".py", ".md"}:
            return False

        try:
            relative_path = file_path.resolve().relative_to(self.plugins_dir)
        except ValueError:
            return False

        if len(relative_path.parts) < 2:
            return False

        plugin_dir = self.plugins_dir / relative_path.parts[0]
        return plugin_dir.is_dir() or relative_path.parts[0] in self.loaded_plugins

    def _plugin_name_from_path(self, file_path: Path) -> str | None:
        try:
            relative_path = file_path.resolve().relative_to(self.plugins_dir)
        except ValueError:
            return None

        if not relative_path.parts:
            return None
        return relative_path.parts[0]

    def _schedule_plugin_sync(self, plugin_name: str, file_name: str) -> None:
        current_time = time.time()
        previous_time = self._plugin_mod_times.get(plugin_name)
        if previous_time is not None and current_time - previous_time < self.reload_debounce_seconds:
            return
        self._plugin_mod_times[plugin_name] = current_time

        loop = self._event_loop
        if loop is None or loop.is_closed():
            self.logger.warning(f"事件循环不可用，跳过插件 {plugin_name} 的热重载")
            return

        def queue_task() -> None:
            existing_task = self._pending_sync_tasks.get(plugin_name)
            if existing_task is not None and not existing_task.done():
                return

            self.logger.info(f"检测到插件 {plugin_name} 文件变更({file_name})，准备同步插件状态")
            task = loop.create_task(self._sync_plugin_state(plugin_name))
            self._pending_sync_tasks[plugin_name] = task
            task.add_done_callback(lambda _: self._pending_sync_tasks.pop(plugin_name, None))

        loop.call_soon_threadsafe(queue_task)

    async def _sync_plugin_state(self, plugin_name: str) -> None:
        plugin_dir = self.plugins_dir / plugin_name
        plugin_exists = plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists()
        plugin_loaded = plugin_name in self.loaded_plugins

        try:
            if plugin_exists and plugin_loaded:
                await self.reload_plugin(plugin_name)
            elif plugin_exists:
                await self.load_plugin(plugin_name)
            elif plugin_loaded:
                await self.unload_plugin(plugin_name)
                self.logger.info(f"插件 {plugin_name} 文件已移除，已自动卸载")
        except Exception as exc:
            self.logger.error(f"同步插件 {plugin_name} 状态失败: {exc}", exc_info=True)

    def _load_plugin_meta(self, plugin_name: str, plugin_dir: Path, package_module: Any) -> PluginMeta:
        dependencies = getattr(package_module, "plugin_dependencies", None)
        if dependencies is None:
            dependencies = getattr(package_module, "dependencies", [])

        description = getattr(package_module, "plugin_description", "")
        declared_name = getattr(package_module, "plugin_name", plugin_name)

        return PluginMeta(
            name=declared_name,
            description=description,
            dependencies=list(dependencies or []),
            module_name=self._plugin_module_name(plugin_name),
            path=str(plugin_dir),
        )

    def _load_plugin_modules(self, plugin_name: str) -> list[Any]:
        plugin_dir = self.plugins_dir / plugin_name
        modules: list[Any] = []

        for module_path in sorted(plugin_dir.glob("*.py"), key=lambda item: item.name):
            if module_path.name == "__init__.py":
                continue
            module_name = f"{self._plugin_module_name(plugin_name)}.{module_path.stem}"
            module = importlib.import_module(module_name)
            modules.append(module)

        return modules

    def _discover_plugin_classes(self, modules: list[Any]) -> list[type[PluginInterface]]:
        discovered: list[type[PluginInterface]] = []

        for module in modules:
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj is PluginInterface:
                    continue
                if not issubclass(obj, PluginInterface):
                    continue
                if obj.__module__ != module.__name__:
                    continue
                discovered.append(obj)

        return discovered

    async def _invoke_callable(self, func: Any, context: PluginRuntimeContext) -> None:
        await self._invoke_with_supported_kwargs(
            func,
            bot=context,
            config=self.config,
            context=context,
            plugin_manager=self,
        )

    async def _invoke_plugin_instance(self, instance: PluginInterface, context: PluginRuntimeContext) -> None:
        setup = getattr(instance, "setup", None)
        if setup is not None and setup.__func__ is not PluginInterface.setup:
            await self._invoke_with_supported_kwargs(
                setup,
                bot=context,
                config=self.config,
                context=context,
                plugin_manager=self,
            )
            return

        start = getattr(instance, "start", None)
        if start is not None:
            await self._invoke_with_supported_kwargs(
                start,
                bot=context,
                config=self.config,
                context=context,
                plugin_manager=self,
            )

    async def _invoke_with_supported_kwargs(self, func: Any, **kwargs: Any) -> Any:
        signature = inspect.signature(func)
        accepted = {
            name: value
            for name, value in kwargs.items()
            if name in signature.parameters
        }
        result = func(**accepted)
        if inspect.isawaitable(result):
            return await result
        return result

    def _unregister_handlers(self, context: PluginRuntimeContext) -> None:
        event_bus = getattr(self.bot, "event_bus", None)
        if event_bus is None:
            return

        for event_type, handler in context.registered_handlers:
            handlers = event_bus.handlers.get(event_type)
            if not handlers:
                continue
            handlers.discard(handler)
            if not handlers:
                del event_bus.handlers[event_type]

    def _clear_plugin_modules_from_cache(self, plugin_name: str) -> None:
        module_prefixes = self._plugin_module_prefixes(plugin_name)
        module_names = [
            module_name
            for module_name in list(sys.modules.keys())
            if any(
                module_name == prefix or module_name.startswith(prefix + ".")
                for prefix in module_prefixes
            )
        ]

        module_names.sort(key=lambda item: item.count("."), reverse=True)
        for module_name in module_names:
            sys.modules.pop(module_name, None)

        importlib.invalidate_caches()


__all__ = [
    "PluginInterface",
    "PluginManager",
    "PluginMeta",
    "PluginRuntimeContext",
]

