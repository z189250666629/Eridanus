"""Password-protected archive helpers hosted under core.toolkit."""

from __future__ import annotations

from typing import List, Optional, Union

from .installer import install_and_import
from .util import Util

pyzipper = install_and_import("pyzipper")
util = Util.get_instance()


def compress_files_with_pwd(
    sources: Union[str, List[str]],
    output_dir: str,
    zip_name: str = "archive.zip",
    password: Optional[str] = None,
):
    return util.file.compress_files_with_pwd(sources, output_dir, zip_name, password)


__all__ = ["compress_files_with_pwd", "pyzipper"]
