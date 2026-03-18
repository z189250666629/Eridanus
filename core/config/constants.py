"""Configuration-related constants hosted under core.config."""

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = APP_ROOT.parent

PLUGINS_DIR = str(APP_ROOT / "plugins")
PLUGINS_MODULE_PREFIX = "plugins"

# Prefer the app-local `Eridanus/config/` after migration, while keeping the
# repo-level `config/` as a temporary fallback during the final cutover.
CORE_CONFIG_DIR = (
    str(APP_ROOT / "config"),
    str(REPO_ROOT / "config"),
    "config",
)
PLUGIN_DIR_EXCLUDES = {"__pycache__", "common_config"}

__all__ = [
    "CORE_CONFIG_DIR",
    "PLUGIN_DIR_EXCLUDES",
    "PLUGINS_DIR",
    "PLUGINS_MODULE_PREFIX",
]
