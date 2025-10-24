# utils/tone_memory.py
import json
import os

STATE_FILE = "buffer/tone_state.json"

def save_tone_state(tone: str):
    """儲存當前語氣狀態"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_tone": tone}, f, ensure_ascii=False, indent=2)
    print(f"💾 已儲存語氣狀態：{tone}")

def load_tone_state() -> str:
    """讀取上次語氣狀態"""
    if not os.path.exists(STATE_FILE):
        return "default"
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        tone = data.get("last_tone", "default")
        print(f"🪶 上次語氣狀態：{tone}")
        return tone

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

