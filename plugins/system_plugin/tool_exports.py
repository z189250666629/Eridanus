"""Lightweight tool wrappers for func_map dynamic imports.

Avoid importing heavy runtime modules at tool-map build time. The actual
implementations remain in `func_collection.py` and are loaded only when a tool
is invoked.
"""

from __future__ import annotations


def _func_collection():
    from plugins.system_plugin import func_collection

    return func_collection


async def call_user_data_register(bot, event, config):
    return await _func_collection().call_user_data_register(bot, event, config)


async def call_user_data_query(bot, event, config):
    return await _func_collection().call_user_data_query(bot, event, config)


async def call_user_data_sign(bot, event, config):
    return await _func_collection().call_user_data_sign(bot, event, config)


async def call_change_city(bot, event, config, city):
    return await _func_collection().call_change_city(bot, event, config, city)


async def call_permit(bot, event, config, target_id, level, type="user"):
    return await _func_collection().call_permit(bot, event, config, target_id, level, type)


async def call_delete_user_history(bot, event, config):
    return await _func_collection().call_delete_user_history(bot, event, config)


async def call_clear_all_history(bot, event, config):
    return await _func_collection().call_clear_all_history(bot, event, config)


async def operate_group_push_tasks(bot, event, config, task_type, operation, target_uid=None):
    return await _func_collection().operate_group_push_tasks(
        bot,
        event,
        config,
        task_type,
        operation,
        target_uid,
    )


__all__ = [
    "call_user_data_register",
    "call_user_data_query",
    "call_user_data_sign",
    "call_change_city",
    "call_permit",
    "call_delete_user_history",
    "call_clear_all_history",
    "operate_group_push_tasks",
]

