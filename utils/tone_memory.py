# utils/tone_memory.py
from functools import lru_cache
import os, json

STATE_FILE = "buffer/tone_state.json"


def save_tone_state(tone: str):
    """儲存當前語氣狀態"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"tone": tone}, f, ensure_ascii=False, indent=2)
    print(f"💾 已儲存語氣狀態：{tone}")
    # ✅ 修正：縮排必須正確（這行在函式內）
    load_tone_state.cache_clear()


@lru_cache(maxsize=10)
def load_tone_state():
    """
    快取最近的 tone 狀態，避免重複讀檔。
    自動保存最近 10 次呼叫結果。
    """
    path = STATE_FILE
    if not os.path.exists(path):
        return "default"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("tone", "default")

# -------------------------------------
# 語氣轉移邏輯（漸變系統）
# -------------------------------------

TONE_TRANSITION = {
    "sad": ["calm", "reflective"],
    "reflective": ["deep", "calm"],
    "deep": ["calm", "relaxed"],
    "calm": ["relaxed", "default"],
    "relaxed": ["light", "default"],
    "light": ["relaxed", "default"],
    "default": ["default"]
}

import random

def transition_tone(current: str) -> str:
    """
    根據當前語氣，自動轉移到下一個可能語氣
    """
    options = TONE_TRANSITION.get(current, ["default"])
    next_tone = random.choice(options)
    print(f"🌗 語氣轉移：{current} → {next_tone}")
    save_tone_state(next_tone)
    return next_tone

