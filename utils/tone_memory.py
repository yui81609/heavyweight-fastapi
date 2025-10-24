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
