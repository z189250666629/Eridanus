"""File processing helpers hosted under core.toolkit."""

from __future__ import annotations

import os
import re
import zipfile
from typing import List, Optional, Union

import httpx
import pyzipper

from .base import BaseTool
from .pdf_encrypt import AsyncPDFEncryptor


class FileProcessor(BaseTool):
    def __init__(self):
        super().__init__(self.__class__.__name__)
        self.encryptor = AsyncPDFEncryptor()

    async def encrypt_pdf_file(self, input_path: str, output_path: str, password: str):
        """Encrypt a PDF file asynchronously."""
        return await self.encryptor.encrypt_pdf_file(input_path, output_path, password)

    async def download_file(self, url, path, proxy=None) -> str:
        """Download a file to the provided path."""
        if proxy:
            proxies = {"http://": proxy, "https://": proxy}
        else:
            proxies = None

        async with httpx.AsyncClient(proxies=proxies, timeout=None) as client:
            response = await client.get(url)
            with open(path, "wb") as f:
                f.write(response.content)
            return path

    def sanitize_filename(self, name: str, replacement: str = "_") -> str:
        return re.sub(r'[\\/:"*?<>|]', replacement, name)

    def compress_files(self, sources: Union[str, List[str]], output_dir: str, zip_name: str = "archive.zip"):
        """Compress one or more files/directories into a zip archive."""
        zip_name = self.sanitize_filename(zip_name)
        if isinstance(sources, str):
            sources = [sources]

        os.makedirs(output_dir, exist_ok=True)
        output_zip = os.path.join(output_dir, zip_name)

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for source in sources:
                if os.path.isfile(source):
                    zipf.write(source, os.path.basename(source))
                elif os.path.isdir(source):
                    for root, _, files in os.walk(source):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source))
                            zipf.write(file_path, arcname)
                else:
                    self.logger.warning(f"跳过无效路径：{source}")

        self.logger.info(f"压缩完成，文件保存在：{output_zip}")

    def compress_files_with_pwd(
        self,
        sources: Union[str, List[str]],
        output_dir: str,
        zip_name: str = "archive.zip",
        password: Optional[str] = None,
    ):
        """Compress one or more files/directories into an encrypted zip archive."""
        zip_name = self.sanitize_filename(zip_name)
        if isinstance(sources, str):
            sources = [sources]

        os.makedirs(output_dir, exist_ok=True)
        output_zip = os.path.join(output_dir, zip_name)

        with pyzipper.AESZipFile(
            output_zip,
            "w",
            compression=pyzipper.ZIP_DEFLATED,
            encryption=pyzipper.WZ_AES,
        ) as zipf:
            if password:
                zipf.setpassword(password.encode("utf-8"))
                zipf.setencryption(pyzipper.WZ_AES, nbits=256)

            for source in sources:
                if os.path.isfile(source):
                    zipf.write(source, os.path.basename(source))
                elif os.path.isdir(source):
                    for root, _, files in os.walk(source):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source))
                            zipf.write(file_path, arcname)
                else:
                    self.logger.warning(f"跳过无效路径：{source}")

        self.logger.info(f"压缩完成，文件保存在：{output_zip}")

    def merge_audio_files(self, audio_files: list, output_file: str) -> str:
        """
        Merge audio files and export as a single file.

        Supported output formats: mp3, wav, flac.
        """
        self.logger.info(f"合并音频文件...{audio_files}")
        if not audio_files:
            raise ValueError("音频文件列表不能为空。")

        from pydub import AudioSegment

        combined = AudioSegment.empty()
        for file in audio_files:
            audio = AudioSegment.from_file(file)
            combined += audio

        file_format = output_file.split(".")[-1].lower()
        if file_format not in ["mp3", "wav", "flac"]:
            raise ValueError(f"不支持的输出格式：{file_format}")

        combined.export(output_file, format=file_format)
        return output_file


__all__ = ["FileProcessor"]
