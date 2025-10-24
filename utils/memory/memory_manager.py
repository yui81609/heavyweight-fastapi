# app/utils/memory/memory_manager.py
import os
import json
import asyncio
import logging
import threading
import time
from datetime import datetime
from collections import deque
from textwrap import shorten
from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError

# ============================================================
# ⚙️ 設定與初始化
# ============================================================
MEMORY_FILE = "buffer/conversation_memory.json"
MAX_HISTORY = 30
SUMMARY_LIMIT = 600
SYNC_INTERVAL = 12 * 60 * 60  # 每 12 小時同步一次
SYNC_BATCH_SIZE = 20          # 每次最多同步幾條記憶

conversation_buffer = deque(maxlen=MAX_HISTORY)

logger = logging.getLogger("memory")
logger.setLevel(logging.INFO)

# ============================================================
# 💬 對話緩衝與摘要壓縮
# ============================================================
def add_message(role: str, content: str):
    """新增一條訊息進記憶池。"""
    conversation_buffer.append({"role": role, "content": content})


def summarize_context() -> str:
    """壓縮最近對話為摘要（取最後 15 條）"""
    text = " ".join([m["content"] for m in list(conversation_buffer)[-15:]])
    summary = shorten(text, width=SUMMARY_LIMIT, placeholder=" ...")
    return f"摘要：{summary}"


def maintain_context():
    """超過上限時自動壓縮"""
    if len(conversation_buffer) >= MAX_HISTORY:
        summary = summarize_context()
        trimmed = list(conversation_buffer)[-5:]
        conversation_buffer.clear()
        conversation_buffer.append({"role": "system", "content": summary})
        conversation_buffer.extend(trimmed)
        logger.info("✂️ Context compressed.")


# ============================================================
# 💾 記憶保存與載入
# ============================================================
def save_memory():
    """保存摘要至 JSON 檔案"""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    summary = summarize_context()
    entry = {"timestamp": datetime.now().isoformat(), "summary": summary}

    try:
        data = []
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.append(entry)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 已保存對話記憶（目前 {len(data)} 條）")
        conversation_buffer.clear()
    except Exception as e:
        logger.warning(f"⚠️ 保存記憶失敗: {e}")


async def save_memory_async():
    """非同步版本（不阻塞主線程）"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, save_memory)


def load_memory(limit: int = 3):
    """讀取最近幾條記憶摘要"""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[-limit:]
    except json.JSONDecodeError:
        return []


def restore_recent_memory(limit: int = 5):
    """開機時自動載入歷史摘要"""
    memories = load_memory(limit)
    for m in memories:
        conversation_buffer.append({
            "role": "system",
            "content": f"（前次摘要）{m['summary']}"
        })
    logger.info(f"🧠 已恢復 {len(memories)} 條歷史摘要。")


# ============================================================
# 🗄️ 長期記憶同步到資料庫（安全批次）
# ============================================================
def sync_to_db(project_id="default"):
    """
    將 JSON 記憶摘要批次同步到 PostgreSQL。
    """
    try:
        # 動態導入以避免循環引用
        from app.main import engine, memories

        if not os.path.exists(MEMORY_FILE):
            logger.info("📭 無可同步記憶。")
            return

        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            logger.info("📭 記憶檔為空，跳過同步。")
            return

        batch = data[-SYNC_BATCH_SIZE:]

        with engine.begin() as conn:
            for entry in batch:
                conn.execute(
                    insert(memories).values(
                        project_id=project_id,
                        content=entry["summary"],
                        tags=["long-term", "memory"],
                        created_at=datetime.fromisoformat(entry["timestamp"]),
                    )
                )

        logger.info(f"🧩 已批次同步 {len(batch)} 條記憶至資料庫。")

    except (SQLAlchemyError, Exception) as e:
        logger.warning(f"⚠️ 同步記憶到資料庫失敗: {e}")


def schedule_sync_to_db():
    """
    每 12 小時自動執行一次長期記憶同步。
    """
    def loop():
        while True:
            sync_to_db()
            time.sleep(SYNC_INTERVAL)
    threading.Thread(target=loop, daemon=True).start()
    logger.info("🕓 長期記憶自動同步任務已啟動。")


# ============================================================
# 🚀 初始化
# ============================================================
def init_memory_system():
    """在伺服器啟動時初始化記憶系統"""
    restore_recent_memory()
    schedule_sync_to_db()
    logger.info("✅ 記憶系統初始化完成（含長期同步）")
