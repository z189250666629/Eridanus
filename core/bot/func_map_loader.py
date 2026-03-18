"""Legacy-compatible tool registry helpers hosted under core.bot."""

from __future__ import annotations

import importlib
import os
import traceback
from pathlib import Path

from core.config import PLUGINS_DIR, PLUGINS_MODULE_PREFIX, PLUGIN_DIR_EXCLUDES
from core.toolkit.logger import get_logger

from .func_map import FuncMap
from .skill_parser import parse_plugin_skill

logger = get_logger("func_map_loader")
dynamic_imports = {}
all_function_declarations = []
func_map_registry = FuncMap()


def _sync_legacy_exports() -> None:
    dynamic_imports.clear()
    all_function_declarations.clear()

    for registration in func_map_registry._plugins.values():
        dynamic_imports.update(registration.dynamic_imports)
        all_function_declarations.extend(registration.function_declarations)


def _iter_plugin_packages(plugin_path: Path, module_prefix: str):
    for child in sorted(plugin_path.iterdir()):
        if not child.is_dir():
            continue
        if child.name in PLUGIN_DIR_EXCLUDES or child.name.startswith("."):
            continue
        if not (child / "__init__.py").exists():
            continue
        yield child, f"{module_prefix}.{child.name}"


def scan_plugins(plugin_dir: str = PLUGINS_DIR, module_prefix: str = PLUGINS_MODULE_PREFIX):
    plugin_path = Path(plugin_dir)
    if not plugin_path.is_absolute():
        plugin_path = (Path(os.getcwd()) / plugin_path).resolve()
    else:
        plugin_path = plugin_path.resolve()

    func_map_registry._plugins.clear()
    _sync_legacy_exports()

    if not plugin_path.exists():
        logger.warning(f"⚠️ 插件目录不存在，跳过扫描: {plugin_path}")
        return dynamic_imports

    for root, module_name in _iter_plugin_packages(plugin_path, module_prefix):
        try:
            module = importlib.import_module(module_name)

            if hasattr(module, "dynamic_imports"):
                if not isinstance(module.dynamic_imports, (dict, list)):
                    logger.warning(f"⚠️ {module_name}.dynamic_imports 格式不正确")
                    continue

                module_dynamic_imports = module.dynamic_imports
                if isinstance(module_dynamic_imports, list):
                    module_dynamic_imports = {
                        module_name: [func.__name__ for func in module_dynamic_imports if callable(func)]
                    }
                skill_document = parse_plugin_skill(root)

                func_map_registry.register(
                    module_name,
                    dynamic_imports=module_dynamic_imports,
                    function_declarations=getattr(module, "function_declarations", []),
                    skill_documents=[skill_document] if skill_document is not None else [],
                )

        except Exception as exc:
            logger.error(f"❌ 无法导入 {module_name}: {exc}")
            traceback.print_exc()
            continue

    _sync_legacy_exports()
    return dynamic_imports


def build_tool_map():
    return func_map_registry.build_tool_map()


def build_tool_fixed_params(bot=None, event=None, config=None):
    fixed = {}
    if bot is not None:
        fixed["bot"] = bot
    if event is not None:
        fixed["event"] = event
    if config is not None:
        fixed["config"] = config
    return {"all": fixed}


def get_tool_declarations(config=None):
    declarations = func_map_registry.get_declarations(config)
    all_function_declarations[:] = declarations
    return declarations


def filter_tools_by_config(tools, config=None):
    return func_map_registry.filter_tools_by_config(tools, config)


def get_skill_documents(plugin_name=None):
    return func_map_registry.get_skill_documents(plugin_name)


__all__ = [
    "all_function_declarations",
    "build_tool_fixed_params",
    "build_tool_map",
    "dynamic_imports",
    "filter_tools_by_config",
    "func_map_registry",
    "get_skill_documents",
    "get_tool_declarations",
    "scan_plugins",
]
