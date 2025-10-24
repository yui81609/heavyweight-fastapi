# utils/background_cleaner.py
import os
import json
import gzip
import time
from datetime import datetime, timedelta

BUFFER_DIR = "buffer"
PENDING_FILE = os.path.join(BUFFER_DIR, "pending.jsonl")
LOG_FILE = os.path.join(BUFFER_DIR, "system_clean.log")

def _write_log(message: str):
    os.makedirs(BUFFER_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")

def clean_pending(threshold_hours: int = 24):
    """
    清除過舊暫存內容 (> threshold_hours)
    並壓縮成 .gz 備份
    """
    if not os.path.exists(PENDING_FILE):
        return 0

    cutoff = datetime.now() - timedelta(hours=threshold_hours)
    cleaned, kept = [], []

    with open(PENDING_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                ts = data.get("timestamp")
                if ts and datetime.fromisoformat(ts) < cutoff:
                    cleaned.append(data)
                else:
                    kept.append(line.strip())
            except Exception:
                continue

    # 壓縮舊資料
    if cleaned:
        archive = os.path.join(BUFFER_DIR, f"pending_{int(time.time())}.gz")
        with gzip.open(archive, "wt", encoding="utf-8") as gz:
            for item in cleaned:
                gz.write(json.dumps(item, ensure_ascii=False) + "\n")
        _write_log(f"🧹 壓縮並清理 {len(cleaned)} 條暫存 -> {archive}")

    # 寫回保留資料
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept))

    return len(cleaned)

def periodic_cleanup(interval_hours: int = 6):
    """每隔 interval_hours 週期清理一次"""
    while True:
        try:
            removed = clean_pending(24)
            if removed:
                _write_log(f"✅ 清除 {removed} 條過期暫存")
        except Exception as e:
            _write_log(f"⚠️ 清理錯誤：{e}")
        time.sleep(interval_hours * 3600)
