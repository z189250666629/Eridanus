"""Text helpers hosted under core.toolkit."""

from __future__ import annotations

import random
import string

import httpx
import requests

from .base import BaseTool


class TextProcessor(BaseTool):
    """文本处理工具"""

    def __init__(self):
        super().__init__(self.__class__.__name__)

    def generate_random_str(self, length: int = 6) -> str:
        self.logger.info("Generating random string with length %d", length)
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    async def translate(self, text, mode="ZH_CN2JA"):
        try:
            url = f"https://api.pearktrue.cn/api/translate/?text={text}&type={mode}"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.get(url)
                return r.json()["data"]["translate"]
        except Exception:
            if mode != "ZH_CN2JA":
                return text

        try:
            url = f"https://findmyip.net/api/translate.php?text={text}&target_lang=ja"
            r = requests.get(url=url, timeout=10)
            return r.json()["data"]["translate_result"]
        except Exception:
            pass

        try:
            url = f"https://translate.appworlds.cn?text={text}&from=zh-CN&to=ja"
            r = requests.get(url=url, timeout=10, verify=False)
            return r.json()["data"]
        except Exception:
            pass

        return text


__all__ = ["TextProcessor"]
