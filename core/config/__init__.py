"""Configuration facade."""

from .constants import CORE_CONFIG_DIR, PLUGIN_DIR_EXCLUDES, PLUGINS_DIR, PLUGINS_MODULE_PREFIX
from .manager import YAMLManager
from .schema import (
    ConfigValidationError,
    validate_basic_config,
    validate_censor_config,
    validate_censor_group_config,
    validate_censor_user_config,
    validate_core_config,
    validate_menu_config,
)

__all__ = [
    "CORE_CONFIG_DIR",
    "ConfigValidationError",
    "PLUGIN_DIR_EXCLUDES",
    "PLUGINS_DIR",
    "PLUGINS_MODULE_PREFIX",
    "YAMLManager",
    "validate_basic_config",
    "validate_censor_config",
    "validate_censor_group_config",
    "validate_censor_user_config",
    "validate_core_config",
    "validate_menu_config",
]
