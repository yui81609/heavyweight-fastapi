# app/utils/memory/context_manager.py
from collections import deque
from textwrap import shorten

MAX_HISTORY = 30
history = deque(maxlen=MAX_HISTORY)

def add_message(role: str, content: str):
    """把對話記錄起來"""
    history.append({"role": role, "content": content})

def summarize_context():
    """壓縮前段對話成摘要"""
    text = " ".join([m["content"] for m in list(history)[:-5]])
    summary = shorten(text, width=500, placeholder=" ...")
    return f"摘要：{summary}"

def maintain_context():
    """當對話太多，壓縮前文、保留摘要"""
    if len(history) >= MAX_HISTORY:
        summary = summarize_context()
        trimmed = list(history)[-5:]
        history.clear()
        history.append({"role": "system", "content": summary})
        history.extend(trimmed)
        print("🧹 Context compressed")

