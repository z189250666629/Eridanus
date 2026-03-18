"""Archive helpers hosted under core.toolkit."""

from __future__ import annotations

from typing import List, Union

from .util import Util

util = Util.get_instance()


def sanitize_filename(name: str, replacement: str = "_") -> str:
    return util.file.sanitize_filename(name, replacement)


def compress_files(sources: Union[str, List[str]], output_dir: str, zip_name: str = "archive.zip"):
    return util.file.compress_files(sources, output_dir, zip_name)


__all__ = ["compress_files", "sanitize_filename"]
