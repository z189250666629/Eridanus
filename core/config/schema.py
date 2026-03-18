"""Core configuration schema validation helpers."""

from __future__ import annotations

from numbers import Real
from typing import Any


class ConfigValidationError(ValueError):
    """Raised when a managed core configuration file is structurally invalid."""


def _expect_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigValidationError(f"`{path}` must be a mapping, got {type(value).__name__}")
    return value


def _expect_str(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise ConfigValidationError(f"`{path}` must be a string, got {type(value).__name__}")
    return value


def _expect_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigValidationError(f"`{path}` must be a boolean, got {type(value).__name__}")
    return value


def _expect_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(f"`{path}` must be an integer, got {type(value).__name__}")
    return value


def _expect_number(value: Any, path: str) -> Real:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ConfigValidationError(f"`{path}` must be a number, got {type(value).__name__}")
    return value


def _expect_int_or_str(value: Any, path: str) -> int | str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ConfigValidationError(f"`{path}` must be an integer or string, got {type(value).__name__}")
    return value


def _expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigValidationError(f"`{path}` must be a list, got {type(value).__name__}")
    return value


def _expect_choice(value: Any, path: str, choices: set[str]) -> str:
    text = _expect_str(value, path)
    if text not in choices:
        joined = ", ".join(sorted(choices))
        raise ConfigValidationError(f"`{path}` must be one of: {joined}; got {text!r}")
    return text


def validate_basic_config(data: Any) -> None:
    root = _expect_mapping(data, "basic_config")

    _expect_choice(root.get("user_handle_logic"), "basic_config.user_handle_logic", {"blacklist", "whitelist"})
    _expect_int(root.get("user_handle_logic_operate_level"), "basic_config.user_handle_logic_operate_level")
    _expect_choice(root.get("group_handle_logic"), "basic_config.group_handle_logic", {"blacklist", "whitelist"})
    _expect_int(root.get("group_handle_logic_operate_level"), "basic_config.group_handle_logic_operate_level")
    _expect_int(root.get("邀请bot加群所需权限"), "basic_config.邀请bot加群所需权限")
    _expect_int(root.get("申请bot好友所需权限"), "basic_config.申请bot好友所需权限")

    webui = _expect_mapping(root.get("webui"), "basic_config.webui")
    _expect_bool(webui.get("enable"), "basic_config.webui.enable")

    _expect_bool(root.get("record_mface"), "basic_config.record_mface")

    proxy = _expect_mapping(root.get("proxy"), "basic_config.proxy")
    _expect_str(proxy.get("http_proxy"), "basic_config.proxy.http_proxy")
    _expect_str(proxy.get("socks_proxy"), "basic_config.proxy.socks_proxy")

    _expect_str(root.get("bot"), "basic_config.bot")

    master = _expect_mapping(root.get("master"), "basic_config.master")
    _expect_str(master.get("name"), "basic_config.master.name")
    _expect_int(master.get("id"), "basic_config.master.id")

    _expect_int(root.get("group"), "basic_config.group")

    adapter = _expect_mapping(root.get("adapter"), "basic_config.adapter")
    _expect_str(adapter.get("name"), "basic_config.adapter.name")
    _expect_bool(adapter.get("use_new_core_bot"), "basic_config.adapter.use_new_core_bot")
    ws_client = _expect_mapping(adapter.get("ws_client"), "basic_config.adapter.ws_client")
    _expect_str(ws_client.get("ws_link"), "basic_config.adapter.ws_client.ws_link")

    plugin_load = _expect_mapping(root.get("PluginLoadConfig"), "basic_config.PluginLoadConfig")
    _expect_choice(
        plugin_load.get("load_strategy"),
        "basic_config.PluginLoadConfig.load_strategy",
        {"batch_loading", "all_at_once", "memory_aware"},
    )
    _expect_int(plugin_load.get("batch_size"), "basic_config.PluginLoadConfig.batch_size")
    _expect_number(plugin_load.get("batch_delay"), "basic_config.PluginLoadConfig.batch_delay")
    _expect_int(plugin_load.get("max_retries"), "basic_config.PluginLoadConfig.max_retries")
    _expect_number(plugin_load.get("retry_delay"), "basic_config.PluginLoadConfig.retry_delay")
    _expect_number(plugin_load.get("memory_threshold_mb"), "basic_config.PluginLoadConfig.memory_threshold_mb")
    _expect_bool(
        plugin_load.get("enable_gc_between_batches"),
        "basic_config.PluginLoadConfig.enable_gc_between_batches",
    )

    handler_monitor = _expect_mapping(root.get("HandlerMonitor"), "basic_config.HandlerMonitor")
    _expect_bool(handler_monitor.get("enable"), "basic_config.HandlerMonitor.enable")
    _expect_number(
        handler_monitor.get("handler_timeout_warning"),
        "basic_config.HandlerMonitor.handler_timeout_warning",
    )

    redis = _expect_mapping(root.get("redis"), "basic_config.redis")
    _expect_int_or_str(redis.get("redis_ip"), "basic_config.redis.redis_ip")
    _expect_int_or_str(redis.get("redis_port"), "basic_config.redis.redis_port")
    _expect_int_or_str(redis.get("redis_db"), "basic_config.redis.redis_db")


def validate_menu_config(data: Any) -> None:
    root = _expect_mapping(data, "menu")
    help_menu = _expect_mapping(root.get("help_menu"), "menu.help_menu")
    _expect_bool(help_menu.get("send_as_node"), "menu.help_menu.send_as_node")
    _expect_str(help_menu.get("send_text"), "menu.help_menu.send_text")
    content = _expect_mapping(help_menu.get("content"), "menu.help_menu.content")
    if not content:
        raise ConfigValidationError("`menu.help_menu.content` must not be empty")


def validate_censor_config(data: Any, *, config_name: str) -> None:
    root = _expect_mapping(data, config_name)
    for list_name in ("blacklist", "whitelist"):
        entries = _expect_list(root.get(list_name), f"{config_name}.{list_name}")
        for index, entry in enumerate(entries):
            _expect_int_or_str(entry, f"{config_name}.{list_name}[{index}]")


def validate_censor_group_config(data: Any) -> None:
    validate_censor_config(data, config_name="censor_group")


def validate_censor_user_config(data: Any) -> None:
    validate_censor_config(data, config_name="censor_user")


def validate_core_config(plugin_name: str | None, config_name: str, data: Any) -> None:
    if plugin_name != "common_config":
        return
    if config_name == "basic_config":
        validate_basic_config(data)
    elif config_name == "menu":
        validate_menu_config(data)
    elif config_name == "censor_group":
        validate_censor_group_config(data)
    elif config_name == "censor_user":
        validate_censor_user_config(data)


__all__ = [
    "ConfigValidationError",
    "validate_basic_config",
    "validate_censor_config",
    "validate_censor_group_config",
    "validate_censor_user_config",
    "validate_core_config",
    "validate_menu_config",
]
