import json
import requests
import os
import time

# 定義暫存與成功上傳紀錄檔
BUFFER_FILE = "buffer/pending.jsonl"
UPLOADED_FILE = "buffer/uploaded.jsonl"

def save_to_buffer(data):
    """當伺服器沒回應時，把資料暫存在本地"""
    os.makedirs(os.path.dirname(BUFFER_FILE), exist_ok=True)
    with open(BUFFER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    print("📦 已暫存待上傳資料。")

def retry_upload():
    """重新上傳暫存在本地的資料"""
    if not os.path.exists(BUFFER_FILE):
        print("🪶 沒有暫存資料。")
        return
    new_pending = []
    with open(BUFFER_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if not line.strip():
            continue
        data = json.loads(line)
        try:
            r = requests.post(data["url"], json=data["payload"], timeout=10)
            r.raise_for_status()
            with open(UPLOADED_FILE, "a", encoding="utf-8") as log:
                log.write(json.dumps(data, ensure_ascii=False) + "\n")
            print("✅ 上傳成功：", data["payload"].get("content", "")[:30])
        except Exception as e:
            print("⚠️ 上傳失敗，保留暫存：", e)
            new_pending.append(data)
    # 覆寫 buffer，只保留未成功的
    with open(BUFFER_FILE, "w", encoding="utf-8") as f:
        for item in new_pending:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def safe_upload(payload, url):
    """安全上傳：若失敗則暫存"""
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print("✅ 即時上傳成功。")
    except Exception as e:
        print("❌ 上傳失敗，原因：", e)
        save_to_buffer({"url": url, "payload": payload})
