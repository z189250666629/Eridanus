"""Plugin entrypoint discovery helpers hosted under core.bot."""

from __future__ import annotations

import importlib
import importlib.util
import sys
import traceback
from pathlib import Path
from typing import Callable

from core.config import PLUGINS_MODULE_PREFIX
from core.toolkit.logger import get_logger

logger = get_logger("main_func_detector")


def _is_plugin_submodule(module_name: str) -> bool:
    prefix = f"{PLUGINS_MODULE_PREFIX}."
    if not module_name.startswith(prefix):
        return False

    relative_name = module_name[len(prefix):]
    return "." in relative_name


def check_has_main(module_name: str) -> tuple[bool, object]:
    try:
        if module_name in sys.modules:
            del sys.modules[module_name]

        modules_to_remove = [name for name in sys.modules.keys() if name.startswith(module_name + ".")]
        for mod_name in modules_to_remove:
            del sys.modules[mod_name]

        if module_name in sys.modules:
            module = sys.modules[module_name]
            return hasattr(module, "main") and callable(getattr(module, "main")), module

        try:
            module = importlib.import_module(module_name)
            return hasattr(module, "main") and callable(getattr(module, "main")), module
        except (ImportError, KeyError, AttributeError):
            pass

        spec = importlib.util.find_spec(module_name)
        if spec is None:
            logger.warning(f"⚠️ 未找到模块 {module_name}")
            return False, None

        if spec.loader is None:
            logger.warning(f"⚠️ 模块 {module_name} 没有加载器")
            return False, None

        if module_name in sys.modules:
            module = sys.modules[module_name]
            if not hasattr(module, "__file__"):
                import time

                time.sleep(0.01)
                if module_name in sys.modules:
                    module = sys.modules[module_name]
            return hasattr(module, "main") and callable(getattr(module, "main")), module

        module = importlib.util.module_from_spec(spec)
        placeholder = type(sys)("placeholder")
        placeholder.__file__ = getattr(spec, "origin", "")
        sys.modules[module_name] = placeholder

        parts = module_name.split(".")
        for i in range(1, len(parts)):
            parent_name = ".".join(parts[:i])
            if parent_name not in sys.modules:
                try:
                    parent_spec = importlib.util.find_spec(parent_name)
                    if parent_spec and parent_spec.loader:
                        parent_module = importlib.util.module_from_spec(parent_spec)
                        parent_placeholder = type(sys)("placeholder")
                        parent_placeholder.__file__ = getattr(parent_spec, "origin", "")
                        sys.modules[parent_name] = parent_placeholder
                        parent_spec.loader.exec_module(parent_module)
                        sys.modules[parent_name] = parent_module
                except Exception:
                    pass

        try:
            spec.loader.exec_module(module)
            sys.modules[module_name] = module
            return hasattr(module, "main") and callable(getattr(module, "main")), module
        except Exception as exec_error:
            if module_name in sys.modules:
                del sys.modules[module_name]
            raise exec_error

    except Exception as exc:
        if not _is_plugin_submodule(module_name):
            logger.warning(f"⚠️ 加载模块 {module_name} 失败， \n{exc}")
            traceback.print_exc()
        else:
            logger.debug(f"跳过不可加载的插件模块 {module_name}: {exc}")
        return False, None


def load_main_functions(init_file: str) -> list[Callable]:
    entrance_func: list[Callable] = []
    module_names: list[str] = []

    dir_path = Path(init_file).parent
    subpackage = dir_path.name

    for file_path in dir_path.glob("*.py"):
        if file_path.name == "__init__.py":
            continue
        module_name = file_path.stem
        full_module_name = f"{PLUGINS_MODULE_PREFIX}.{subpackage}.{module_name}"

        has_main, module = check_has_main(full_module_name)
        if has_main:
            entrance_func.append(module.main)
            module_names.append(module_name)

    if not module_names:
        logger.warning(f"{init_file} 未找到任何可用的 entrance_func")

    return entrance_func


__all__ = ["check_has_main", "load_main_functions"]
