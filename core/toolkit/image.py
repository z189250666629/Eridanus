"""Image processing helpers hosted under core.toolkit."""

from __future__ import annotations

import base64
import random
import re
import string
from io import BytesIO

import httpx
from PIL import Image

from .base import BaseTool


class ImageProcessor(BaseTool):
    def __init__(self):
        super().__init__(self.__class__.__name__)

    async def Image2Base64(self, url: str) -> str:
        """Fetch an image URL and return its base64 content."""
        async with httpx.AsyncClient(timeout=9000) as client:
            response = await client.get(url)
            if response.status_code == 200:
                image_bytes = response.content
                return base64.b64encode(image_bytes).decode("utf-8")
            raise Exception(f"Failed to retrieve image: {response.status_code}")

    async def download_img(self, url, path=None, gray_layer=False, proxy=None, headers=None) -> str:
        """Download an image or decode a data URI into a local file."""
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


__all__ = ["ImageProcessor"]
