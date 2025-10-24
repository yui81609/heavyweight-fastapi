# app/utils/memory/memory_manager.py
import json
import os
from datetime import datetime
from textwrap import shorten
from collections import deque

MEMORY_FILE = "buffer/conversation_memory.json"
conversation_buffer = deque(maxlen=30)

def add_message(role: str, content: str):
    conversation_buffer.append({"role": role, "content": content})

def summarize_recent_dialogue():
    text = " ".join([m["content"] for m in list(conversation_buffer)])
    summary = shorten(text, width=600, placeholder=" ...")
    return summary

def save_memory():
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    summary = summarize_recent_dialogue()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
    }

    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    data.append(entry)

    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"💾 已保存對話記憶（目前 {len(data)} 條）")
    conversation_buffer.clear()

def load_memory(limit=3):
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    return data[-limit:]
