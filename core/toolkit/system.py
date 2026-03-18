"""Legacy system helpers hosted under core.toolkit."""

from __future__ import annotations

from pip._internal.cli.main import main as pip_main

from .base import BaseTool
from .installer import install_and_import as shared_install_and_import


def _ensure_pip_index_configured():
    try:
        pip_main(["config", "set", "global.index-url", "https://mirrors.aliyun.com/pypi/simple/"])
    except Exception:
        # Keep legacy behavior best-effort; importing the module should not fail
        # just because the environment disallows writing pip user config.
        return


class SystemProcessor(BaseTool):
    def __init__(self):
        super().__init__(self.__class__.__name__)

    def install_and_import(self, package_name, import_name=None):
        """Install a package via the shared requirements-aware installer."""
        _ensure_pip_index_configured()
        return shared_install_and_import(package_name, import_name)


__all__ = ["SystemProcessor"]
