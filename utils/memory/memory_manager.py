# app/utils/memory/memory_manager.py
import os
import json
import asyncio
import logging
from datetime import datetime
from collections import deque
from textwrap import shorten

# ============================================================
# ⚙️ 基本設定
# ============================================================
MEMORY_FILE = "buffer/conversation_memory.json"
MAX_HISTORY = 30  # 對話緩衝上限
SUMMARY_LIMIT = 600  # 摘要字數上限

conversation_buffer = deque(maxlen=MAX_HISTORY)

# 設定 logger（取代 print，部署時更乾淨）
logger = logging.getLogger("memory")
logger.setLevel(logging.INFO)

# ============================================================
# 🧠 對話操作
# ============================================================
def add_message(role: str, content: str):
    """
    新增一條對話訊息進記憶緩衝。
    """
    conversation_buffer.append({"role": role, "content": content})


def summarize_context() -> str:
    """
    壓縮最近對話為摘要，用於記憶保存。
    只取最近 15 條內容以減少負擔。
    """
    text = " ".join([m["content"] for m in list(conversation_buffer)[-15:]])
    summary = shorten(text, width=SUMMARY_LIMIT, placeholder=" ...")
    return f"摘要：{summary}"


def maintain_context():
    """
    若對話過多，自動壓縮並保留摘要。
    """
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
    """
    將目前對話摘要寫入 JSON 檔案。
    """
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    summary = summarize_context()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
    }

    # 讀取舊資料
    data = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("⚠️ 記憶檔案已損壞，將重新建立。")

    # 寫入新資料
    data.append(entry)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 已保存對話記憶（目前 {len(data)} 條）")
    conversation_buffer.clear()


async def save_memory_async():
    """
    異步版本的 save_memory（不阻塞主線程）。
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, save_memory)


def load_memory(limit: int = 3):
    """
    載入最近幾條對話記憶摘要。
    """
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[-limit:]
    except json.JSONDecodeError:
        return []


def restore_recent_memory(limit: int = 5):
    """
    啟動時自動恢復最近的對話摘要。
    """
    memories = load_memory(limit)
    for m in memories:
        conversation_buffer.append({
            "role": "system",
            "content": f"（前次摘要）{m['summary']}"
        })
    logger.info(f"🧠 已恢復 {len(memories)} 條歷史摘要。")


# ============================================================
# 🚀 啟動初始化
# ============================================================
def init_memory():
    """
    初始化記憶模組（通常在 app 啟動時呼叫）
    """
    restore_recent_memory()
    logger.info("✅ 記憶系統初始化完成。")
