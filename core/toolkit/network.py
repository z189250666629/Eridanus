"""Network helpers hosted under core.toolkit."""

from __future__ import annotations

import base64
import random
import re
import string
from io import BytesIO
from typing import Optional

import httpx
import requests
from PIL import Image

from .base import BaseTool


class NetworkProcessor(BaseTool):
    _UA_SERVICES = [
        "https://httpbin.org/user-agent",
        "http://httpbin.org/user-agent",
    ]

    def __init__(self):
        super().__init__()
        self._client = httpx.AsyncClient(headers={}, timeout=60)

    def _fetch_ua_sync(self) -> Optional[str]:
        self.logger.info("Fetching User-Agent...")
        for service in self._UA_SERVICES:
            try:
                resp = requests.get(service, timeout=10)
                if resp.status_code == 200:
                    ua = resp.json().get("user-agent", "").strip()
                    if ua:
                        return ua
            except Exception as e:
                print(f"从 {service} 获取 UA 失败: {e}")
                continue
        return None

    def random_headers(self) -> dict:
        user_agent_list = [
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
            "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
            "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        ]

        return {"User-Agent": random.choice(user_agent_list)}

    async def download_img(self, url, path=None, gray_layer=False, proxy=None, headers=None) -> str:
        """Legacy convenience wrapper shared with ImageProcessor."""
        if path is None:
            characters = string.ascii_letters + string.digits
            random_string = "".join(random.choice(characters) for _ in range(10))
            path = f"data/pictures/cache/{random_string}.jpg"
        if url.startswith("data:image"):
            match = re.match(r"data:image/(.*?);base64,(.+)", url)
            if not match:
                raise ValueError("Invalid Data URI format")
            _img_type, base64_data = match.groups()
            img_data = base64.b64decode(base64_data)
            try:
                with open(path, "wb") as f:
                    f.write(img_data)
            finally:
                del img_data
            return path

        if proxy:
            proxies = {"http://": proxy, "https://": proxy}
        else:
            proxies = None

        async with httpx.AsyncClient(proxies=proxies, headers=headers) as client:
            response = await client.get(url)
            if gray_layer:
                img = None
                try:
                    img = Image.open(BytesIO(response.content))
                    image_black_white = img.convert("1")
                    image_black_white.save(path)
                finally:
                    if img is not None:
                        img.close()
                    del response
            else:
                try:
                    with open(path, "wb") as f:
                        f.write(response.content)
                finally:
                    del response

            return path

    async def download_file(self, url, path, proxy=None) -> str:
        if proxy:
            proxies = {"http://": proxy, "https://": proxy}
        else:
            proxies = None
        async with httpx.AsyncClient(proxies=proxies, timeout=None) as client:
            response = await client.get(url)
            with open(path, "wb") as f:
                f.write(response.content)
            return path

    async def get(self, url, *, params=None, headers=None, cookies=None):
        return await self._client.get(url, params=params, headers=headers, cookies=cookies)

    async def post(self, url, *, data=None, files=None, headers=None, cookies=None):
        return await self._client.post(url, data=data, files=files, headers=headers, cookies=cookies)

    async def post_json(self, url, *, json=None, headers=None, cookies=None):
        return await self._client.post(url, json=json, headers=headers, cookies=cookies)


__all__ = ["NetworkProcessor"]
