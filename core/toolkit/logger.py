"""Unified logger implementation hosted under core.toolkit."""

import logging
import os
import threading
from datetime import datetime

import colorlog

_logger = None
_blocked_loggers = ["INFO_MSG", "DEBUG"]
_lock = threading.Lock()
_current_log_date = None


class CategoryHandler(logging.StreamHandler):
    """Custom handler that switches formatter by message category."""

    def __init__(self):
        super().__init__()
        self.formatters = {
            "default": self._create_formatter(
                "%(log_color)s%(asctime)s [%(name)s] - %(levelname)s - [bot] %(message)s",
                {"DEBUG": "white", "INFO": "cyan", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"},
            ),
            "msg": self._create_formatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - [MSG] %(message)s",
                {"DEBUG": "white", "INFO": "green", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"},
            ),
            "func": self._create_formatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - [FUNC] %(message)s",
                {"DEBUG": "white", "INFO": "blue", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"},
            ),
            "server": self._create_formatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - [SERVER] %(message)s",
                {"DEBUG": "white", "INFO": "purple", "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"},
            ),
        }
        self.setFormatter(self.formatters["default"])

    def _create_formatter(self, format_str, colors):
        return colorlog.ColoredFormatter(format_str, log_colors=colors)

    def emit(self, record):
        category = getattr(record, "category", "default")
        formatter = self.formatters.get(category, self.formatters["default"])

        with _lock:
            original_formatter = self.formatter
            self.setFormatter(formatter)
            try:
                super().emit(record)
            finally:
                self.setFormatter(original_formatter)


def createLogger(blocked_loggers=None):
    global _logger, _blocked_loggers, _current_log_date
    if blocked_loggers is not None:
        _blocked_loggers = blocked_loggers

    log_folder = "log"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    logger = logging.getLogger("Eridanus")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    class BlockLoggerFilter(logging.Filter):
        def filter(self, record):
            if record.levelname in _blocked_loggers:
                return False
            category = getattr(record, "category", None)
            if category and f"INFO_{category.upper()}" in _blocked_loggers:
                return False
            return True

    console_handler = CategoryHandler()
    console_handler.addFilter(BlockLoggerFilter())
    logger.addHandler(console_handler)

    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    _current_log_date = datetime.now().strftime("%Y-%m-%d")
    log_file_path = os.path.join(log_folder, f"{_current_log_date}.log")

    file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(BlockLoggerFilter())
    logger.addHandler(file_handler)

    logger._file_handler = file_handler
    logger._log_folder = log_folder
    logger._file_formatter = file_formatter
    logger._block_filter = BlockLoggerFilter()

    def update_log_file():
        global _current_log_date
        new_date = datetime.now().strftime("%Y-%m-%d")
        if new_date != _current_log_date:
            old_date = _current_log_date
            new_log_file_path = os.path.join(logger._log_folder, f"{new_date}.log")

            logger.removeHandler(logger._file_handler)
            logger._file_handler.close()

            logger._file_handler = logging.FileHandler(new_log_file_path, mode="a", encoding="utf-8")
            logger._file_handler.setFormatter(logger._file_formatter)
            logger._file_handler.addFilter(logger._block_filter)
            logger.addHandler(logger._file_handler)

            _current_log_date = new_date
            print(f"日志文件已从 {old_date}.log 切换到: {new_log_file_path}")

    def check_date_change():
        global _current_log_date
        current_date = datetime.now().strftime("%Y-%m-%d")
        return current_date != _current_log_date

    logger.check_date_change = check_date_change
    logger.update_log_file = update_log_file
    _logger = logger


class LoggerWrapper:
    """Logger wrapper that preserves the legacy helper methods."""

    def __init__(self, logger, custom_name=None):
        self._logger = logger
        self._custom_name = custom_name or "Eridanus"

    def _check_and_update_log_file(self):
        if hasattr(self._logger, "check_date_change") and self._logger.check_date_change():
            with _lock:
                if self._logger.check_date_change():
                    self._logger.update_log_file()

    def _log_with_category(self, level, message, category=None, *args, **kwargs):
        self._check_and_update_log_file()
        record = self._logger.makeRecord(self._custom_name, level, __file__, 0, message, args, None)
        if category:
            record.category = category
        self._logger.handle(record)

    def debug(self, message, *args, **kwargs):
        pass

    def info(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.INFO):
            self._log_with_category(logging.INFO, message, None, *args, **kwargs)

    def success(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.INFO):
            self._log_with_category(logging.INFO, message, None, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.WARNING):
            self._log_with_category(logging.WARNING, message, None, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.ERROR):
            self._log_with_category(logging.ERROR, message, None, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.CRITICAL):
            self._log_with_category(logging.CRITICAL, message, None, *args, **kwargs)

    def info_msg(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.INFO) and "INFO_MSG" not in _blocked_loggers:
            self._log_with_category(logging.INFO, message, "msg", *args, **kwargs)

    def info_func(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.INFO) and "INFO_FUNC" not in _blocked_loggers:
            self._log_with_category(logging.INFO, message, "func", *args, **kwargs)

    def server(self, message, *args, **kwargs):
        if self._logger.isEnabledFor(logging.INFO) and "SERVER" not in _blocked_loggers:
            self._log_with_category(logging.INFO, message, "server", *args, **kwargs)

    def update_log_file(self):
        if hasattr(self._logger, "update_log_file"):
            with _lock:
                self._logger.update_log_file()


def get_logger(name=None, blocked_loggers=None) -> LoggerWrapper:
    global _logger
    with _lock:
        if _logger is None:
            createLogger(blocked_loggers)
    return LoggerWrapper(_logger, name)


def _set_current_log_date_for_test(date_str):
    global _current_log_date, _logger

    if _logger is not None:
        _logger.removeHandler(_logger._file_handler)
        _logger._file_handler.close()

        new_log_file_path = os.path.join(_logger._log_folder, f"{date_str}.log")
        _logger._file_handler = logging.FileHandler(new_log_file_path, mode="a", encoding="utf-8")
        _logger._file_handler.setFormatter(_logger._file_formatter)
        _logger._file_handler.addFilter(_logger._block_filter)
        _logger.addHandler(_logger._file_handler)

        print(f"测试: 切换到日期 {date_str} 的日志文件: {new_log_file_path}")

    _current_log_date = date_str


def _get_current_log_date():
    global _current_log_date
    return _current_log_date


__all__ = [
    "CategoryHandler",
    "LoggerWrapper",
    "createLogger",
    "get_logger",
    "_get_current_log_date",
    "_set_current_log_date_for_test",
]
