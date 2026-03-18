"""LLM conversation storage hosted under core.database."""

import asyncio
import base64
import html
import json
import os
import re

import aiosqlite
from PIL import Image

from core.config import YAMLManager

_history_db_initialized = False
_charas_db_initialized = False
_CHARAS_DB_FILE = "data/dataBase/charas.db"


def _get_local_config():
    return YAMLManager.get_instance().ai_llm.config


def _get_database_file():
    local_config = _get_local_config()
    if local_config["llm"]["model"] == "gemini":
        return "data/dataBase/conversation.db"
    return "data/dataBase/openai_conversation.db"


async def ensure_history_db_initialized():
    global _history_db_initialized
    if not _history_db_initialized:
        await init_db()
        _history_db_initialized = True


async def ensure_charas_db_initialized():
    global _charas_db_initialized
    if not _charas_db_initialized:
        await init_charas_db()
        _charas_db_initialized = True


async def use_folder_chara(file_name):
    full_path = f"data/system/chara/{file_name}"
    if file_name.endswith((".txt", ".json")):
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    if file_name.endswith((".jpg", ".jpeg", ".png")):
        return silly_tavern_card(full_path, clear_html=True)


async def get_folder_chara():
    chara_list = [f for f in os.listdir("data/system/chara")]
    return "\n".join(chara_list)


def clean_invalid_characters(s, clear_html=False):
    cleaned = "".join(c for c in s if ord(c) >= 32 or c in ("\t", "\n", "\r"))
    if clear_html:
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r"<[^>]+>.*?</[^>]+>", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<[^>]+?/>", "", cleaned)
        cleaned = re.sub(r"^.*?(?=:|：)", "", cleaned).lstrip(":： ").lstrip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    cleaned = cleaned.replace("{{user}}", "{用户}").replace("{{char}}", "{bot_name}")
    return cleaned.strip()


def silly_tavern_card(image_path, clear_html=False):
    image = Image.open(image_path)

    try:
        for _, v in image.text.items():
            _ = v[:100]
    except AttributeError:
        return "错误，没有文本块信息"

    final = []

    try:
        for key, value in image.info.items():
            if isinstance(value, str) and "chara" in key.lower():
                decoded = base64.b64decode(value)
                res = decoded.decode("utf-8", errors="ignore")
                final.append(res)
    except Exception as exc:
        return f"错误，解码失败: {exc}"

    if final:
        s = "\n".join(final)
        return clean_invalid_characters(s, clear_html=clear_html)
    return "错误，没有人设信息"


async def init_db():
    database_file = _get_database_file()
    async with aiosqlite.connect(database_file) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                user_id INTEGER PRIMARY KEY,
                history TEXT
            )
        """
        )
        await db.commit()


async def init_charas_db():
    async with aiosqlite.connect(_CHARAS_DB_FILE) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_chara (
                user_id INTEGER PRIMARY KEY,
                chara TEXT
            )
        """
        )
        await db.commit()


async def change_folder_chara(file_name, user_id, folder_path="data/system/chara"):
    try:
        await ensure_charas_db_initialized()
        folder_contents = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

        for item in folder_contents:
            if file_name in item:
                file_name = item

        if file_name in folder_contents:
            chara = await use_folder_chara(file_name)
            if chara.startswith("错误"):
                return chara
            await delete_user_history(user_id)
            async with aiosqlite.connect(_CHARAS_DB_FILE) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO user_chara (user_id, chara) VALUES (?, ?)",
                    (user_id, chara),
                )
                await db.commit()

            return "人设已切换为：" + file_name
        return f"文件{file_name}不存在"
    except Exception as exc:
        return f"发生了一个错误: {exc}"


async def set_all_users_chara(file_name, folder_path="data/system/chara"):
    try:
        await ensure_history_db_initialized()
        await ensure_charas_db_initialized()

        if not os.path.isfile(os.path.join(folder_path, file_name)):
            return f"文件{file_name}不存在"

        chara = await use_folder_chara(file_name)
        if chara.startswith("错误"):
            return chara

        await clear_all_history()

        async with aiosqlite.connect(_get_database_file()) as db:
            cursor = await db.execute("SELECT user_id FROM conversation_history")
            history_users = await cursor.fetchall()

        async with aiosqlite.connect(_CHARAS_DB_FILE) as db:
            cursor = await db.execute("SELECT user_id FROM user_chara")
            chara_users = await cursor.fetchall()

            all_user_ids = set(user[0] for user in history_users).union(user[0] for user in chara_users)
            for user_id in all_user_ids:
                await db.execute(
                    "INSERT OR REPLACE INTO user_chara (user_id, chara) VALUES (?, ?)",
                    (user_id, chara),
                )

            await db.commit()

        return "所有用户（包括历史记录中的用户）的人设已切换为：" + file_name
    except Exception as exc:
        return f"发生了一个错误: {exc}"


async def clear_all_users_chara():
    try:
        await ensure_charas_db_initialized()
        await clear_all_history()
        async with aiosqlite.connect(_CHARAS_DB_FILE) as db:
            await db.execute("DELETE FROM user_chara")
            await db.commit()
        return "所有用户的人设已清空"
    except Exception as exc:
        return f"发生了一个错误: {exc}"


async def clear_user_chara(user_id):
    try:
        await ensure_charas_db_initialized()
        await delete_user_history(user_id)
        async with aiosqlite.connect(_CHARAS_DB_FILE) as db:
            await db.execute("DELETE FROM user_chara WHERE user_id = ?", (user_id,))
            await db.commit()

        return f"用户ID为 {user_id} 的人设已删除"
    except Exception as exc:
        return f"发生了一个错误: {exc}"


async def read_chara(user_id, chara_str):
    if not isinstance(chara_str, str):
        raise ValueError("chara_str 必须是字符串类型")

    await ensure_charas_db_initialized()

    async with aiosqlite.connect(_CHARAS_DB_FILE) as db:
        cursor = await db.execute("SELECT chara FROM user_chara WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        if result is None:
            return chara_str
        return result[0]


async def get_user_history(user_id) -> list:
    await ensure_history_db_initialized()

    async with aiosqlite.connect(_get_database_file()) as db:
        async with db.execute("SELECT history FROM conversation_history WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return json.loads(result[0])
            return []


async def delete_latest2_history(user_id):
    user_history = await get_user_history(user_id)
    user_history = user_history[:-2]
    await update_user_history(user_id, user_history)


async def update_user_history(user_id, history):
    """更新用户历史对话，自动过滤掉思维链(thought)内容。"""

    await ensure_history_db_initialized()

    filtered_history = []
    for msg in history:
        if isinstance(msg, dict) and "parts" in msg:
            filtered_parts = [
                part for part in msg["parts"] if not (isinstance(part, dict) and part.get("thought") is True)
            ]
            if filtered_parts:
                filtered_history.append({"role": msg.get("role", "user"), "parts": filtered_parts})
        else:
            filtered_history.append(msg)

    async with aiosqlite.connect(_get_database_file()) as db:
        await db.execute(
            "INSERT OR REPLACE INTO conversation_history (user_id, history) VALUES (?, ?)",
            (user_id, json.dumps(filtered_history)),
        )
        await db.commit()


async def delete_user_history(user_id):
    await ensure_history_db_initialized()

    async with aiosqlite.connect(_get_database_file()) as db:
        await db.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
        await db.commit()


async def clear_all_history():
    await ensure_history_db_initialized()

    async with aiosqlite.connect(_get_database_file()) as db:
        await db.execute("DELETE FROM conversation_history")
        await db.commit()


__all__ = [
    "change_folder_chara",
    "clean_invalid_characters",
    "clear_all_history",
    "clear_all_users_chara",
    "clear_user_chara",
    "delete_latest2_history",
    "delete_user_history",
    "ensure_charas_db_initialized",
    "ensure_history_db_initialized",
    "get_folder_chara",
    "get_user_history",
    "init_charas_db",
    "init_db",
    "read_chara",
    "set_all_users_chara",
    "silly_tavern_card",
    "update_user_history",
    "use_folder_chara",
]
