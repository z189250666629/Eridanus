"""Shared toolkit facade over legacy ToolKits and framework utils."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AsyncPDFEncryptor",
    "AsyncWebClient",
    "BaseTool",
    "GeminiKeyManager",
    "MemoryMonitor",
    "NoAvailableAPIKeyError",
    "Translator",
    "Util",
    "async_download_file",
    "async_request",
    "check_and_install_playwright",
    "compress_files",
    "compress_files_with_pwd",
    "convert_list_to_type",
    "delay_recall",
    "delete_old_files_async",
    "download_file",
    "download_img",
    "get_headers",
    "get_img",
    "get_logger",
    "get_web_client",
    "install_and_import",
    "merge_audio_files",
    "parse_arguments",
    "random_session_hash",
    "random_str",
    "sanitize_filename",
    "url_to_base64",
]


def __getattr__(name: str) -> Any:
    if name == "Util":
        return import_module(".util", __name__).Util
    if name == "BaseTool":
        return import_module(".base", __name__).BaseTool
    if name == "delete_old_files_async":
        return import_module(".gc_tool", __name__).delete_old_files_async
    if name == "install_and_import":
        return import_module(".installer", __name__).install_and_import
    if name == "get_logger":
        return import_module(".logger", __name__).get_logger
    if name == "MemoryMonitor":
        return import_module(".memory", __name__).MemoryMonitor
    if name in {"random_session_hash", "random_str"}:
        module = import_module(".random_utils", __name__)
        return getattr(module, name)
    if name in {
        "convert_list_to_type",
        "delay_recall",
        "download_file",
        "download_img",
        "get_headers",
        "get_img",
        "merge_audio_files",
        "parse_arguments",
        "url_to_base64",
    }:
        module = import_module(".compat_utils", __name__)
        return getattr(module, name)
    if name in {"AsyncWebClient", "async_download_file", "async_request", "get_web_client"}:
        module = import_module(".async_web_client", __name__)
        return getattr(module, name)
    if name in {"GeminiKeyManager", "NoAvailableAPIKeyError"}:
        module = import_module(".gemini_keys", __name__)
        return getattr(module, name)
    if name == "Translator":
        return import_module(".translator", __name__).Translator
    if name == "AsyncPDFEncryptor":
        return import_module(".pdf_encrypt", __name__).AsyncPDFEncryptor
    if name in {"compress_files", "sanitize_filename"}:
        module = import_module(".archive", __name__)
        return getattr(module, name)
    if name == "compress_files_with_pwd":
        return import_module(".archive_pwd", __name__).compress_files_with_pwd
    if name == "check_and_install_playwright":
        return import_module(".playwright_installer", __name__).check_and_install_playwright
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
