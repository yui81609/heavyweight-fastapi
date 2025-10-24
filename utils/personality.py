# utils/personality.py
import json
import os
from collections import deque, Counter
from functools import lru_cache
import asyncio

# ✅ 正確導入記憶模組
from utils.memory.memory_manager import add_message, save_memory_async

STATE_FILE = "buffer/personality_state.json"

# 🧠 短期語氣記錄
tone_history = deque(maxlen=10)

# 🌿 初始理解模型狀態
default_personality = {
    "empathy": 0.7,       # 同理心強度（理解、傾聽）
    "familiarity": 0.5,   # 熟悉度（語氣自然、親切）
    "last_emotion": "neutral",
}


@lru_cache(maxsize=5)
def load_personality():
    """快取目前理解模型狀態"""
    if not os.path.exists(STATE_FILE):
        return default_personality
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_personality


def save_personality(state: dict):
    """儲存理解模型狀態"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    load_personality.cache_clear()
    print(f"💾 [理解模型] empathy={state['empathy']:.2f}, familiarity={state['familiarity']:.2f}")


async def update_understanding(tone: str) -> dict:
    """
    根據語氣 tone 更新理解模型（同理心與熟悉度）。
    tone 範例：positive, sad, angry, curious, neutral
    """
    state = load_personality()
    tone_history.append(tone)

    # --- 🌤 調整規則 ---
    if tone in ["sad", "angry"]:
        # 使用者情緒低落或憤怒 → 同理心上升
        state["empathy"] = min(1.0, state["empathy"] + 0.05)
    elif tone in ["positive", "curious"]:
        # 輕鬆、好奇 → 熟悉度上升
        state["familiarity"] = min(1.0, state["familiarity"] + 0.03)
    else:
        # 情緒平靜 → 慢慢回到基準
        state["empathy"] = max(0.6, state["empathy"] - 0.01)
        state["familiarity"] = max(0.4, state["familiarity"] - 0.01)

    # --- 🌈 最近趨勢修正 ---
    if len(tone_history) >= 5:
        freq = Counter(tone_history)
        if freq.get("sad", 0) >= 3:
            state["empathy"] = min(1.0, state["empathy"] + 0.05)
        if freq.get("positive", 0) >= 3:
            state["familiarity"] = min(1.0, state["familiarity"] + 0.05)

    # 記錄最新情緒
    state["last_emotion"] = tone

    # --- 💾 儲存 + 寫入短期記憶 ---
    save_personality(state)
    add_message("assistant", f"Emotion detected: {tone}")
    await save_memory_async()

    return state


def describe_personality() -> str:
    """將目前理解狀態轉成自然描述"""
    s = load_personality()
    if s["empathy"] > 0.8:
        tone = "非常理解你的心情"
    elif s["empathy"] > 0.6:
        tone = "靜靜地聽你說話"
    else:
        tone = "保持溫柔的距離"

    if s["familiarity"] > 0.7:
        closeness = "語氣自然、像老朋友一樣"
    elif s["familiarity"] > 0.5:
        closeness = "語氣親切"
    else:
        closeness = "語氣略顯陌生，但真誠傾聽"

    return f"{tone}，{closeness}。"


