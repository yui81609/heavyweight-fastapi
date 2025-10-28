# app/memory.py
import json
import os
import time
from typing import List, Dict
from app.config import (
    RAW_LOG_PATH,
    CONV_MEMORY_PATH,
    IDENTITY_MEMORY_PATH,
    PENDING_IDENTITY_PATH,
    SUMMARY_WINDOW,
    RECENT_CHUNKS_FOR_CONTEXT,
    MAX_IDENTITY_SNIPPETS,
)
from app.summarizer import summarize_block


def _ensure_file(path: str):
    if not os.path.exists(path):
        with open(path, "w") as f:
            pass  # create empty file


def append_raw_log(user_message: str, assistant_reply: str):
    """把現在這一輪對話寫進 raw_log.jsonl"""
    _ensure_file(RAW_LOG_PATH)
    entry = {
        "ts": time.time(),
        "user": user_message,
        "assistant": assistant_reply,
    }
    with open(RAW_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_raw_log() -> List[Dict]:
    _ensure_file(RAW_LOG_PATH)
    lines = []
    with open(RAW_LOG_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def append_conversation_summary(summary_text: str, open_threads: List[str]):
    """把一段summary存到 conversation_memory.jsonl"""
    _ensure_file(CONV_MEMORY_PATH)
    block = {
        "ts": time.time(),
        "summary": summary_text,
        "open_threads": open_threads,
    }
    with open(CONV_MEMORY_PATH, "a") as f:
        f.write(json.dumps(block, ensure_ascii=False) + "\n")


def load_recent_conversation_chunks(n: int) -> List[str]:
    """抓最近 n 段 summary，回傳純文字列表"""
    _ensure_file(CONV_MEMORY_PATH)
    chunks = []
    with open(CONV_MEMORY_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    chunks = sorted(chunks, key=lambda x: x["ts"], reverse=True)
    recent = []
    for block in chunks[:n]:
        # 把 summary + open_threads 串起來
        recent.append(
            block["summary"]
            + (" | open:" + ", ".join(block["open_threads"]) if block["open_threads"] else "")
        )
    return recent


def maybe_generate_new_summary():
    """
    檢查 raw_log 長度，如果 >= SUMMARY_WINDOW 的倍數，
    就拿最近 SUMMARY_WINDOW 筆對話，叫 summarizer 幫我做一段段落summary，
    存進 conversation_memory.jsonl
    """
    raw = load_raw_log()
    if len(raw) == 0:
        return

    # 我們用整除判斷：每 SUMMARY_WINDOW 筆就產出一個summary
    if len(raw) % SUMMARY_WINDOW != 0:
        return

    recent_block = raw[-SUMMARY_WINDOW:]
    summary_text, open_threads = summarize_block(recent_block)
    append_conversation_summary(summary_text, open_threads)


def save_identity_snippet(key_terms: List[str], snippet: str, note: str = ""):
    """
    手動/半自動 存長期記憶 (identity_memory.jsonl)
    這是穩定的「我是誰」資訊。
    """
    _ensure_file(IDENTITY_MEMORY_PATH)
    block = {
        "ts": time.time(),
        "key_terms": key_terms,
        "snippet": snippet,
        "note": note,
    }
    with open(IDENTITY_MEMORY_PATH, "a") as f:
        f.write(json.dumps(block, ensure_ascii=False) + "\n")


def queue_identity_candidate(user_message: str):
    """
    當使用者講出像「我現在真的想成為可以讓爸媽安心的人」
    這種帶有'我是誰/我要成為誰'的句子，就先丟 pending，之後你人工審。
    """
    _ensure_file(PENDING_IDENTITY_PATH)
    block = {
        "ts": time.time(),
        "candidate": user_message,
    }
    with open(PENDING_IDENTITY_PATH, "a") as f:
        f.write(json.dumps(block, ensure_ascii=False) + "\n")


def load_relevant_identity_snippets(user_message: str) -> List[str]:
    """
    從 identity_memory.jsonl 抓跟當下訊息有關的長期記憶片段。
    超笨實作：keyword match。
    """
    _ensure_file(IDENTITY_MEMORY_PATH)
    with open(IDENTITY_MEMORY_PATH, "r") as f:
        all_rows = [json.loads(l) for l in f if l.strip()]

    msg_lower = user_message.lower()
    scored = []
    for row in all_rows:
        kt = row.get("key_terms", [])
        score = 0
        for term in kt:
            if term.lower() in msg_lower:
                score += 1
        # bonus: if user sounds self-blamey, we might want flare rule
        blame_keywords = ["我是不是退步", "是不是又不行了", "是不是很糟"]
        if any(k in user_message for k in blame_keywords):
            if "flare" in (", ".join(kt).lower()):
                score += 2
        if score > 0:
            scored.append((score, row["snippet"]))

    # sort by score desc, pick top
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for (_, s) in scored[:MAX_IDENTITY_SNIPPETS]]

