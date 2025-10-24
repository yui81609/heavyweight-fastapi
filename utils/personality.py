# utils/personality.py
import json
import os
from collections import deque, Counter
from functools import lru_cache
import asyncio

# ✅ 正確導入（相對路徑）
from utils.memory.memory_manager import add_message, save_memory_async

STATE_FILE = "buffer/personality_state.json"

# 🧠 短期語氣記錄（deque 會自動丟掉最舊的）
tone_history = deque(maxlen=10)

# 初始人格狀態
default_personality = {
    "core_tone": "calm",
    "stability": 0.7,  # 越高代表越難被短期情緒改變
}


@lru_cache(maxsize=5)
def load_personality():
    """快取當前人格狀態，避免重複讀檔"""
    if not os.path.exists(STATE_FILE):
        return default_personality
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_personality


def save_personality(state: dict):
    """儲存人格狀態並清除快取"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    load_personality.cache_clear()
    print(f"💾 已更新人格基調：{state['core_tone']}（穩定度：{state['stability']:.2f}）")


async def update_personality(tone: str) -> dict:
    """
    根據語氣 tone 微調人格狀態。
    - 若語氣連續偏一種方向，會影響 core_tone
    - 穩定度決定人格變化幅度（越高越穩）
    """
    state = load_personality()
    tone_history.append(tone)

    # 統計最近語氣
    tone_count = Counter(tone_history)
    dominant_tone = tone_count.most_common(1)[0][0] if tone_count else "calm"

    # 🌤 根據主要情緒修正人格
    new_tone = state["core_tone"]
    if dominant_tone in ["sad", "gentle", "warm"] and state["stability"] < 0.9:
        new_tone = "warm"
    elif dominant_tone in ["reflective", "rational", "neutral"]:
        new_tone = "calm"
    elif dominant_tone in ["angry", "stressed"]:
        new_tone = "grounded"

    # 穩定度微幅變動
    if dominant_tone == state["core_tone"]:
        state["stability"] = min(1.0, state["stability"] + 0.02)
    else:
        state["stability"] = max(0.5, state["stability"] - 0.05)

    # 人格轉換
    if new_tone != state["core_tone"]:
        print(f"🧭 人格轉換：{state['core_tone']} → {new_tone}")
        state["core_tone"] = new_tone

    # 儲存更新
    save_personality(state)

    # 💬 將語氣更新寫入短期記憶（非同步，避免阻塞）
    add_message("assistant", f"Tone update: {tone}")
    await save_memory_async()

    return state


    
    save_memory()
    return state

