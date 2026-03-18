"""Toolkit base classes hosted under core.toolkit."""

from abc import ABC

from .logger import get_logger


class BaseTool(ABC):
    """Legacy-compatible tool base class."""

    def __init__(self, ToolClsName=None):
        self._initialized = False
        cls_name = ToolClsName if ToolClsName else self.__class__.__name__
        self.logger = get_logger(cls_name)


__all__ = ["BaseTool"]
