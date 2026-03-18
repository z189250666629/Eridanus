"""Database facade with lazy exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AsyncSQLiteDatabase",
    "GroupMessageManager",
    "RedisCacheManager",
    "User",
    "add_user",
    "add_to_group",
    "change_folder_chara",
    "clear_all_group_summaries",
    "clear_all_group_cache",
    "clear_group_summary",
    "clear_group_messages",
    "clear_all_history",
    "clear_all_user_portraits",
    "clear_all_users_chara",
    "clear_user_chara",
    "create_custom_cache_manager",
    "create_group_cache_manager",
    "create_user_cache_manager",
    "delete_latest2_history",
    "delete_user_history",
    "get_folder_chara",
    "get_group_cache_stats",
    "get_group_manager",
    "get_group_messages",
    "get_group_summary",
    "get_last_20_and_convert_to_prompt",
    "get_signed_days",
    "get_user",
    "get_user_history",
    "get_users_with_permission_above",
    "increment_group_message_count",
    "merge_dicts",
    "optimized_batch_update_speeches",
    "read_chara",
    "record_sign_in",
    "set_all_users_chara",
    "should_generate_summary",
    "update_group_summary",
    "update_user",
    "update_user_history",
    "use_folder_chara",
]


def __getattr__(name: str) -> Any:
    if name in {
        "RedisCacheManager",
        "create_custom_cache_manager",
        "create_group_cache_manager",
        "create_user_cache_manager",
    }:
        module = import_module(".redis_cache", __name__)
        return getattr(module, name)

    if name in {
        "clear_all_group_summaries",
        "clear_group_summary",
        "get_group_summary",
        "increment_group_message_count",
        "should_generate_summary",
        "update_group_summary",
    }:
        module = import_module(".group_summary", __name__)
        return getattr(module, name)

    if name in {
        "GroupMessageManager",
        "add_to_group",
        "clear_all_group_cache",
        "clear_group_messages",
        "get_group_messages",
        "get_last_20_and_convert_to_prompt",
    }:
        module = import_module(".group", __name__)
        return getattr(module, name)

    if name == "get_group_cache_stats":
        module = import_module(".group", __name__)
        return getattr(module, "get_cache_stats")

    if name == "get_group_manager":
        module = import_module(".group", __name__)
        return getattr(module, "get_manager")

    if name in {"get_folder_chara", "use_folder_chara"}:
        module = import_module(".llm_db", __name__)
        return getattr(module, name)

    if name in {
        "change_folder_chara",
        "clear_all_history",
        "clear_all_users_chara",
        "clear_user_chara",
        "delete_latest2_history",
        "delete_user_history",
        "get_user_history",
        "read_chara",
        "set_all_users_chara",
        "update_user_history",
    }:
        module = import_module(".llm_db", __name__)
        return getattr(module, name)

    if name in {"AsyncSQLiteDatabase", "merge_dicts", "optimized_batch_update_speeches"}:
        module = import_module(".manshuo_compatible_db", __name__)
        return getattr(module, name)

    if name == "User":
        return import_module(".user", __name__).User

    if name in {
        "add_user",
        "clear_all_user_portraits",
        "get_signed_days",
        "get_user",
        "get_users_with_permission_above",
        "record_sign_in",
        "update_user",
    }:
        module = import_module(".user", __name__)
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
