"""Legacy-compatible Util facade hosted under core.toolkit."""

from __future__ import annotations

from typing import Optional

from .file import FileProcessor
from .image import ImageProcessor
from .network import NetworkProcessor
from .text import TextProcessor


class Util:
    _instance: Optional["Util"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_fields()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Util":
        return cls()

    def _init_fields(self):
        self._network: Optional[NetworkProcessor] = None
        self._image: Optional[ImageProcessor] = None
        self._file: Optional[FileProcessor] = None
        self._text: Optional[TextProcessor] = None

    @property
    def network(self) -> NetworkProcessor:
        if self._network is None:
            self._network = NetworkProcessor()
        return self._network

    @property
    def image(self) -> ImageProcessor:
        if self._image is None:
            self._image = ImageProcessor()
        return self._image

    @property
    def text(self) -> TextProcessor:
        if self._text is None:
            self._text = TextProcessor()
        return self._text

    @property
    def file(self) -> FileProcessor:
        if self._file is None:
            self._file = FileProcessor()
        return self._file


__all__ = ["Util"]
