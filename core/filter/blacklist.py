"""Legacy-compatible blacklist and whitelist filter."""

from __future__ import annotations

from typing import Any

from core.toolkit.compat_utils import convert_list_to_type

from .base import Filter, FilterDecision


class BlacklistFilter(Filter):
    """Preserve the legacy group/user allow-deny semantics from ExtendBot."""

    def __init__(self, config: Any) -> None:
        self.config = config

    async def check(self, event: Any) -> FilterDecision:
        if event is None:
            return FilterDecision(False, "空事件，跳过处理。")

        if hasattr(event, "group_id") and event.group_id is not None:
            group_decision = self._check_group(event.group_id)
            if not group_decision.allowed:
                return group_decision
            if hasattr(event, "user_id"):
                return self._check_user(event.user_id)
            return FilterDecision(True)

        if hasattr(event, "user_id"):
            return self._check_user(event.user_id)

        return FilterDecision(True)

    def _check_group(self, group_id: Any) -> FilterDecision:
        group_logic = self.config.common_config.basic_config["group_handle_logic"]
        group_blacklist = self.config.common_config.censor_group["blacklist"]
        group_whitelist = convert_list_to_type(self.config.common_config.censor_group["whitelist"])

        if group_logic == "blacklist" and group_id in group_blacklist:
            return FilterDecision(False, f"群{group_id}在黑名单中，跳过处理。")
        if group_logic == "whitelist" and group_id not in group_whitelist:
            return FilterDecision(False, f"群{group_id}不在白名单中，跳过处理。")
        return FilterDecision(True)

    def _check_user(self, user_id: Any) -> FilterDecision:
        user_logic = self.config.common_config.basic_config["user_handle_logic"]
        user_blacklist = convert_list_to_type(self.config.common_config.censor_user["blacklist"])
        user_whitelist = convert_list_to_type(self.config.common_config.censor_user["whitelist"])

        if user_logic == "blacklist" and user_id in user_blacklist:
            return FilterDecision(False, f"用户{user_id}在黑名单中，跳过处理。")
        if user_logic == "whitelist" and user_id not in user_whitelist:
            return FilterDecision(False, f"用户{user_id}不在白名单中，跳过处理。")
        return FilterDecision(True)
