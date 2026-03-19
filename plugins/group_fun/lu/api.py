from __future__ import annotations

import asyncio
import random

from core.database import AsyncSQLiteDatabase

from .core import data_init, data_update, date_get, lock_message_select, user_list_get

db = asyncio.run(AsyncSQLiteDatabase.get_instance())


async def _save_lu(userid: str, lu_info: dict) -> None:
    await db.write_user(str(userid), {"lu": lu_info})


def _build_summary(userid: str, lu_info: dict, day_info: dict, title: str) -> str:
    today_key = day_info["day"]
    month_key = day_info["month"]
    year_key = day_info["year"]

    today_times = lu_info["lu_done"]["data"].get(today_key, 0)
    month_times = lu_info["times"]["month"].get(month_key, 0)
    year_times = lu_info["times"]["year"].get(year_key, 0)
    total_times = lu_info["collect"].get("lu_done", 0)
    supple_record = lu_info["lu_supple"].get("record", 0)
    lock_status = "已开启" if lu_info["others"].get("lock_lu") else "未开启"

    return "\n".join(
        [
            title,
            f"用户: {userid}",
            f"今日次数: {today_times}",
            f"本月次数: {month_times}",
            f"今年次数: {year_times}",
            f"累计次数: {total_times}",
            f"补🦌点数: {supple_record}",
            f"贞操锁: {lock_status}",
        ]
    )


async def _send(bot, event, message: str):
    if bot is None or event is None:
        return {"status": "ok", "message": message}
    return await bot.send(event, message)


async def today_lu(userid, times=1, bot=None, event=None, type_check: str = "self"):
    userid = str(userid)
    day_info = await date_get()
    lu_info = await data_init(userid, day_info)

    if lu_info["others"].get("lock_lu"):
        return await _send(bot, event, f"{userid}{random.choice(lock_message_select)}")

    times = max(int(times or 1), 1)
    await data_update(lu_info, {"type": "lu_done", "times": times}, day_info)
    await _save_lu(userid, lu_info)

    title = "今日开🦌成功" if type_check == "self" else "助力开🦌成功"
    return await _send(bot, event, _build_summary(userid, lu_info, day_info, title))


async def no_lu(userid, bot=None, event=None):
    userid = str(userid)
    day_info = await date_get()
    lu_info = await data_init(userid, day_info)
    await data_update(lu_info, {"type": "lu_no", "times": 0}, day_info)
    await _save_lu(userid, lu_info)
    return await _send(bot, event, _build_summary(userid, lu_info, day_info, "今日已戒🦌"))


async def lock_lu(userid, status, bot=None, event=None):
    userid = str(userid)
    lu_info = await data_init(userid)
    lu_info["others"]["lock_lu"] = 1 if status else 0
    await _save_lu(userid, lu_info)
    msg = "贞操锁已开启" if status else "贞操锁已关闭"
    return await _send(bot, event, f"{userid} {msg}")


async def check_lu(userid, bot=None, event=None):
    userid = str(userid)
    day_info = await date_get()
    lu_info = await data_init(userid, day_info)
    return await _send(bot, event, _build_summary(userid, lu_info, day_info, "🦌记录查询"))


async def supple_lu(userid, bot=None, event=None):
    userid = str(userid)
    day_info = await date_get()
    lu_info = await data_init(userid, day_info)

    if lu_info["lu_supple"].get("record", 0) < 3:
        return await _send(bot, event, f"{userid} 的补🦌点数不足，至少需要 3 点。")

    await data_update(lu_info, {"type": "supple_lu", "times": 1}, day_info)
    await _save_lu(userid, lu_info)
    return await _send(bot, event, _build_summary(userid, lu_info, day_info, "补🦌成功"))


async def rank_lu(userid_list, type="month", bot=None, event=None):
    rank_list = await user_list_get([str(userid) for userid in userid_list], type=type)
    if not rank_list:
        return await _send(bot, event, "当前没有可用的🦌排行数据。")

    lines = [f"🦌排行({type})"]
    for index, item in enumerate(rank_list, start=1):
        lines.append(f"{index}. {item['userid']} - {item['times']}")

    return await _send(bot, event, "\n".join(lines))
