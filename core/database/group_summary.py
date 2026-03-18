"""Group summary storage hosted under core.database."""

import datetime
import os

import aiosqlite

from core.toolkit.logger import get_logger

dbpath = "data/dataBase/group_summary.db"
logger = get_logger()

_db_initialized: bool = False


async def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        await initialize_db()
        _db_initialized = True


async def initialize_db():
    try:
        db_dir = os.path.dirname(dbpath)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        async with aiosqlite.connect(dbpath) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute("PRAGMA cache_size=10000;")
            await db.execute("PRAGMA temp_store=MEMORY;")
            await db.execute("PRAGMA busy_timeout=5000;")

            await db.execute(
                """
            CREATE TABLE IF NOT EXISTS group_summaries (
                group_id INTEGER PRIMARY KEY,
                summary TEXT DEFAULT '',
                update_time TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                last_summarized_count INTEGER DEFAULT 0
            )
            """
            )

            required_columns = {
                "summary": 'TEXT DEFAULT ""',
                "update_time": 'TEXT DEFAULT ""',
                "message_count": "INTEGER DEFAULT 0",
                "last_summarized_count": "INTEGER DEFAULT 0",
            }

            async with db.execute("PRAGMA table_info(group_summaries);") as cursor:
                columns = await cursor.fetchall()
                existing_columns = [col[1] for col in columns]

            for column_name, column_def in required_columns.items():
                if column_name not in existing_columns:
                    await db.execute(f"ALTER TABLE group_summaries ADD COLUMN {column_name} {column_def};")

            await db.execute("CREATE INDEX IF NOT EXISTS idx_group_id ON group_summaries(group_id);")
            await db.commit()

    except Exception as exc:
        logger.error(f"群聊总结数据库初始化失败: {exc}")
        raise


async def get_group_summary(group_id: int) -> dict:
    await ensure_db_initialized()
    try:
        async with aiosqlite.connect(dbpath) as db:
            async with db.execute(
                "SELECT summary, update_time, message_count, last_summarized_count FROM group_summaries WHERE group_id = ?",
                (group_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "group_id": group_id,
                        "summary": row[0] or "",
                        "update_time": row[1] or "",
                        "message_count": row[2] or 0,
                        "last_summarized_count": row[3] or 0,
                    }
                return {
                    "group_id": group_id,
                    "summary": "",
                    "update_time": "",
                    "message_count": 0,
                    "last_summarized_count": 0,
                }
    except Exception as exc:
        logger.error(f"获取群聊总结失败: {exc}")
        return {
            "group_id": group_id,
            "summary": "",
            "update_time": "",
            "message_count": 0,
            "last_summarized_count": 0,
        }


async def update_group_summary(
    group_id: int,
    summary: str = None,
    message_count: int = None,
    last_summarized_count: int = None,
):
    await ensure_db_initialized()
    try:
        async with aiosqlite.connect(dbpath) as db:
            async with db.execute("SELECT group_id FROM group_summaries WHERE group_id = ?", (group_id,)) as cursor:
                exists = await cursor.fetchone()

            if not exists:
                await db.execute(
                    "INSERT INTO group_summaries (group_id, summary, update_time, message_count, last_summarized_count) VALUES (?, ?, ?, ?, ?)",
                    (
                        group_id,
                        summary or "",
                        datetime.datetime.now().isoformat(),
                        message_count or 0,
                        last_summarized_count or 0,
                    ),
                )
            else:
                updates = []
                params = []

                if summary is not None:
                    updates.append("summary = ?")
                    params.append(summary)
                    updates.append("update_time = ?")
                    params.append(datetime.datetime.now().isoformat())

                if message_count is not None:
                    updates.append("message_count = ?")
                    params.append(message_count)

                if last_summarized_count is not None:
                    updates.append("last_summarized_count = ?")
                    params.append(last_summarized_count)

                if updates:
                    params.append(group_id)
                    await db.execute(
                        f"UPDATE group_summaries SET {', '.join(updates)} WHERE group_id = ?",
                        params,
                    )

            await db.commit()
            logger.debug(f"群 {group_id} 总结已更新")
    except Exception as exc:
        logger.error(f"更新群聊总结失败: {exc}")


async def increment_group_message_count(group_id: int):
    await ensure_db_initialized()
    try:
        async with aiosqlite.connect(dbpath) as db:
            async with db.execute("SELECT message_count FROM group_summaries WHERE group_id = ?", (group_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.execute(
                    "INSERT INTO group_summaries (group_id, message_count) VALUES (?, 1)",
                    (group_id,),
                )
            else:
                await db.execute(
                    "UPDATE group_summaries SET message_count = message_count + 1 WHERE group_id = ?",
                    (group_id,),
                )

            await db.commit()
    except Exception as exc:
        logger.error(f"增加群消息计数失败: {exc}")


async def clear_group_summary(group_id: int):
    await ensure_db_initialized()
    try:
        async with aiosqlite.connect(dbpath) as db:
            await db.execute(
                "UPDATE group_summaries SET summary = '', update_time = '', last_summarized_count = 0, message_count = 0 WHERE group_id = ?",
                (group_id,),
            )
            await db.commit()
            logger.info(f"群 {group_id} 总结已清除")
    except Exception as exc:
        logger.error(f"清除群聊总结失败: {exc}")


async def clear_all_group_summaries():
    await ensure_db_initialized()
    try:
        async with aiosqlite.connect(dbpath) as db:
            await db.execute(
                "UPDATE group_summaries SET summary = '', update_time = '', last_summarized_count = 0"
            )
            await db.commit()
            logger.info("所有群聊总结已清除")
    except Exception as exc:
        logger.error(f"清除所有群聊总结失败: {exc}")


async def should_generate_summary(group_id: int, interval: int) -> bool:
    info = await get_group_summary(group_id)
    message_count = info.get("message_count", 0)
    last_summarized_count = info.get("last_summarized_count", 0)
    return (message_count - last_summarized_count) >= interval


__all__ = [
    "clear_all_group_summaries",
    "clear_group_summary",
    "ensure_db_initialized",
    "get_group_summary",
    "increment_group_message_count",
    "initialize_db",
    "should_generate_summary",
    "update_group_summary",
]
