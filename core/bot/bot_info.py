"""Startup bot telemetry helpers hosted under core.bot."""

from __future__ import annotations

import platform
import pprint
import uuid

import httpx


def get_system_info():
    system = platform.system()
    machine = platform.machine()
    processor = platform.processor()
    mac_num = hex(uuid.getnode()).replace("0x", "").upper()
    mac = ":".join(mac_num[i : i + 2] for i in range(0, 11, 2))

    return {
        "device_id": mac,
        "system": system,
        "machine": machine,
        "processor": processor,
    }


async def bot_info_collect(botname):
    url = "http://bangumi.manshuo.ink:8092/bot/info_collection"
    device_info = get_system_info()
    data = {"name": botname, "device_info": device_info}
    pprint.pprint(data)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data)
    except Exception as exc:
        print(f"此处报错可忽略： {exc}")


__all__ = ["bot_info_collect", "get_system_info"]
