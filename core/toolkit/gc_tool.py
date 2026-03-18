"""Filesystem cleanup helpers hosted under core.toolkit."""

import asyncio
import os
import time

from .logger import get_logger

logger = get_logger()


async def delete_old_files_async(folder_path):
    """
    异步删除文件夹中过期的文件。
    """

    current_time = time.time()
    time_threshold = 3600
    deleted_file_sizes = []

    async def process_file(file_path):
        nonlocal deleted_file_sizes
        try:
            if file_path.endswith(".py") or file_path.endswith(".ttf"):
                return

            file_mtime = os.path.getmtime(file_path)
            if current_time - file_mtime > time_threshold:
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                deleted_file_sizes.append(file_size)
                await asyncio.to_thread(os.remove, file_path)
        except Exception as exc:
            logger.error(f"处理文件失败: {file_path} - {exc}")

    tasks = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            tasks.append(process_file(file_path))

    await asyncio.gather(*tasks)
    return sum(deleted_file_sizes)


__all__ = ["delete_old_files_async"]
