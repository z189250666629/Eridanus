"""YAML configuration manager hosted under core.config."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ruamel.yaml import YAML

from core.toolkit.installer import install_and_import
from core.toolkit.logger import get_logger

from .constants import CORE_CONFIG_DIR, PLUGINS_DIR
from .schema import ConfigValidationError, validate_core_config

watchdog = install_and_import("watchdog")
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = get_logger("YAMLManager")


class YAMLFileHandler(FileSystemEventHandler):
    def __init__(self, yaml_manager):
        self.yaml_manager = yaml_manager
        self.pending_reloads = {}
        self.debounce_delay = 0.3
        self.lock = threading.Lock()
        super().__init__()

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if file_path.endswith((".yaml", ".yml")):
            self._schedule_reload(file_path)

    def _schedule_reload(self, file_path):
        with self.lock:
            if file_path in self.pending_reloads:
                self.pending_reloads[file_path].cancel()

            timer = threading.Timer(self.debounce_delay, self._execute_reload, args=[file_path])
            self.pending_reloads[file_path] = timer
            timer.start()

    def _execute_reload(self, file_path):
        with self.lock:
            if file_path in self.pending_reloads:
                del self.pending_reloads[file_path]

        self.yaml_manager.reload_file(file_path)


class PluginConfig:
    def __init__(self, name, data, file_paths, save_func):
        self._data = data
        self._file_paths = file_paths
        self._name = name
        self._save_func = save_func

    def __getattr__(self, config_name):
        if config_name in ["_data", "_file_paths", "_save_func", "_name"]:
            return self.__getattribute__(config_name)
        if config_name in self._data:
            return self._data[config_name]
        raise AttributeError(f"Plugin {self._name} has no config '{config_name}'.")

    def __setattr__(self, config_name, value):
        if config_name in ["_data", "_file_paths", "_save_func", "_name"]:
            super().__setattr__(config_name, value)
        elif config_name in self._data:
            self._data[config_name] = value
            self._save_func(config_name, self._name)
        else:
            raise AttributeError(f"Plugin {self._name} has no config '{config_name}'.")


class YAMLManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, plugins_dir=None, core_config_dir=None):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.allow_duplicate_keys = True

        self.data = {}
        self.file_paths = {}
        self.path_to_key = {}
        self.config_roots = self._build_config_roots(plugins_dir, core_config_dir)

        self._load_all_files()
        self._start_file_watcher()

        YAMLManager._instance = self

    def _build_config_roots(self, plugins_dir, core_config_dir):
        root_specs = []

        resolved_core_config_dir = CORE_CONFIG_DIR if core_config_dir is None else core_config_dir
        if isinstance(resolved_core_config_dir, (list, tuple, set)):
            core_root_items = list(resolved_core_config_dir)
        elif resolved_core_config_dir:
            core_root_items = [resolved_core_config_dir]
        else:
            core_root_items = []

        for root in core_root_items:
            root_specs.append({
                "path": self._resolve_root_path(root),
                "root_alias": "common_config",
                "optional": True,
            })

        configured_roots = plugins_dir or PLUGINS_DIR
        if isinstance(configured_roots, (list, tuple, set)):
            root_items = list(configured_roots)
        else:
            root_items = [configured_roots]

        for root in root_items:
            root_specs.append({
                "path": self._resolve_root_path(root),
                "root_alias": None,
                "optional": False,
            })

        existing_roots = []
        for spec in root_specs:
            if os.path.exists(spec["path"]):
                existing_roots.append(spec)
            elif not spec.get("optional", False):
                logger.warning(f"配置目录不存在，已跳过: {spec['path']}")

        if not existing_roots:
            configured_paths = ", ".join(spec["path"] for spec in root_specs) or "<none>"
            raise FileNotFoundError(f"Config directories not found: {configured_paths}")

        return existing_roots

    @staticmethod
    def _resolve_root_path(root):
        root_path = os.fspath(root)
        if os.path.isabs(root_path):
            return os.path.abspath(root_path)
        return os.path.abspath(os.path.join(os.getcwd(), root_path))

    def _load_all_files(self):
        yaml_files = []

        for root_spec in self.config_roots:
            root_path = root_spec["path"]
            root_alias = root_spec["root_alias"]

            for item in os.listdir(root_path):
                item_path = os.path.join(root_path, item)

                if os.path.isdir(item_path):
                    for file_name in os.listdir(item_path):
                        if file_name.endswith((".yaml", ".yml")):
                            file_path = os.path.join(item_path, file_name)
                            config_name = os.path.splitext(file_name)[0]
                            yaml_files.append((item, config_name, file_path))
                elif item.endswith((".yaml", ".yml")):
                    file_path = item_path
                    config_name = os.path.splitext(item)[0]
                    yaml_files.append((root_alias, config_name, file_path))

        def load_yaml_file(args):
            plugin_name, config_name, file_path = args
            yaml_instance = YAML()
            yaml_instance.preserve_quotes = True
            yaml_instance.allow_duplicate_keys = True

            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    data = yaml_instance.load(file)
                validate_core_config(plugin_name, config_name, data)
                return plugin_name, config_name, file_path, data, None
            except ConfigValidationError as exc:
                return plugin_name, config_name, file_path, None, exc
            except Exception as exc:
                logger.info(f"Error loading {file_path}: {exc}")
                return plugin_name, config_name, file_path, {}, None

        validation_errors = []
        with ThreadPoolExecutor() as executor:
            for plugin_name, config_name, file_path, data, validation_error in executor.map(load_yaml_file, yaml_files):
                if validation_error is not None:
                    validation_errors.append(f"{file_path}: {validation_error}")
                    continue
                self._store_config(plugin_name, config_name, file_path, data)

        if validation_errors:
            joined = "\n".join(f"- {item}" for item in validation_errors)
            raise ConfigValidationError(f"Core config validation failed:\n{joined}")

    def _store_config(self, plugin_name, config_name, file_path, data):
        file_path = os.path.abspath(file_path)

        if self._config_exists(plugin_name, config_name):
            logger.debug(f"配置已存在，跳过低优先级文件: {file_path}")
            return

        if plugin_name is None:
            self.data[config_name] = data
            self.file_paths[config_name] = file_path
            self.path_to_key[file_path] = (None, config_name)
            return

        if plugin_name not in self.data:
            self.data[plugin_name] = {}
            self.file_paths[plugin_name] = {}

        self.data[plugin_name][config_name] = data
        self.file_paths[plugin_name][config_name] = file_path
        self.path_to_key[file_path] = (plugin_name, config_name)

    def _config_exists(self, plugin_name, config_name):
        if plugin_name is None:
            return config_name in self.data
        return plugin_name in self.data and config_name in self.data[plugin_name]

    def _start_file_watcher(self):
        self.event_handler = YAMLFileHandler(self)
        self.observer = Observer()
        for root_spec in self.config_roots:
            self.observer.schedule(self.event_handler, root_spec["path"], recursive=True)
        self.observer.start()

    def _update_with_override(self, old_data, new_data):
        from ruamel.yaml.comments import CommentedMap

        if not isinstance(old_data, (dict, CommentedMap)) or not isinstance(new_data, (dict, CommentedMap)):
            return new_data

        old_data.clear()
        for key, value in new_data.items():
            old_data[key] = value

        if isinstance(new_data, CommentedMap) and hasattr(new_data, "ca"):
            if not hasattr(old_data, "ca"):
                old_data.ca = type(new_data.ca)()

            for attr_name in dir(new_data.ca):
                if attr_name.startswith("_"):
                    continue
                try:
                    attr_value = getattr(new_data.ca, attr_name)
                    if not callable(attr_value):
                        setattr(old_data.ca, attr_name, attr_value)
                except Exception:
                    pass

    def reload_file(self, file_path):
        file_path = os.path.abspath(file_path)
        if file_path not in self.path_to_key:
            return

        plugin_name, config_name = self.path_to_key[file_path]

        try:
            yaml_loader = YAML()
            yaml_loader.preserve_quotes = True
            yaml_loader.indent(mapping=2, sequence=4, offset=2)
            yaml_loader.allow_duplicate_keys = True
            yaml_loader.width = 4096

            with open(file_path, "r", encoding="utf-8") as file:
                new_data = yaml_loader.load(file)
            validate_core_config(plugin_name, config_name, new_data)

            if plugin_name is None:
                old_data = self.data[config_name]
                if isinstance(old_data, dict) and isinstance(new_data, dict):
                    self._update_with_override(old_data, new_data)
                else:
                    self.data[config_name] = new_data
            else:
                old_data = self.data[plugin_name][config_name]
                if isinstance(old_data, dict) and isinstance(new_data, dict):
                    self._update_with_override(old_data, new_data)
                else:
                    self.data[plugin_name][config_name] = new_data

            logger.info(f"文件重新加载完成: {file_path}")

        except ConfigValidationError as exc:
            logger.error(f"配置校验失败，已拒绝加载 {file_path}: {exc}")
        except Exception as exc:
            logger.error(f"重新加载文件时出错 {file_path}: {exc}")
            import traceback

            traceback.print_exc()

    def stop_watching(self):
        if hasattr(self, "observer"):
            self.observer.stop()
            self.observer.join()

    @staticmethod
    def get_instance() -> "YAMLManager":
        with YAMLManager._lock:
            if YAMLManager._instance is None:
                YAMLManager._instance = YAMLManager(PLUGINS_DIR, CORE_CONFIG_DIR)
            return YAMLManager._instance

    def save_yaml(self, config_name: str, plugin_name: str = None):
        if plugin_name is None:
            if config_name not in self.file_paths:
                raise ValueError(f"YAML file {config_name} not managed by YAMLManager.")
            file_path = self.file_paths[config_name]
            data = self.data[config_name]
        else:
            if plugin_name not in self.file_paths or config_name not in self.file_paths[plugin_name]:
                raise ValueError(f"YAML file {config_name} in plugin {plugin_name} not managed by YAMLManager.")
            file_path = self.file_paths[plugin_name][config_name]
            data = self.data[plugin_name][config_name]

        with open(file_path, "w", encoding="utf-8") as file:
            self.yaml.dump(data, file)

    def __getattr__(self, name: str):
        if name in self.data:
            if isinstance(self.data[name], dict) and name in self.file_paths and isinstance(self.file_paths[name], dict):
                return PluginConfig(name, self.data[name], self.file_paths[name], self.save_yaml)
            return self.data[name]
        raise AttributeError(f"YAMLManager has no plugin or config '{name}'.")

    def __setattr__(self, name: str, value: Any):
        if name in ["yaml", "data", "file_paths", "path_to_key", "config_roots", "event_handler", "observer", "_instance", "_lock"]:
            super().__setattr__(name, value)
        elif hasattr(self, "data") and name in self.data and not isinstance(self.data[name], dict):
            self.data[name] = value
            self.save_yaml(name)
        else:
            if hasattr(self, "data"):
                raise AttributeError(f"YAMLManager cannot set attribute '{name}' directly.")
            super().__setattr__(name, value)

    def __del__(self):
        self.stop_watching()


__all__ = ["PluginConfig", "YAMLFileHandler", "YAMLManager"]
