# app/main.py
import os, json, asyncio, time, threading, random, math, psutil, requests, shutil, logging
from glob import glob
from typing import List, Optional
from collections import Counter
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, Integer, DateTime, select, func
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert

from utils.uploader import safe_upload, retry_upload, schedule_retry_upload
from utils.memory.memory_manager import init_memory_system
from utils.tone_engine_async import reply as generate_ai_reply
from utils.tone_memory import load_tone_state
from utils.personality import load_personality, save_personality

# -----------------------------------------------------
# 🧾 統一日誌設定
# -----------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# -----------------------------------------------------
# 🚀 FastAPI 初始化
# -----------------------------------------------------
app = FastAPI(
    title="Heavyweight FastAPI",
    version="3.0.0",
    servers=[{"url": "https://heavyweight-fastapi-production-b71c.up.railway.app"}],
)

# -----------------------------------------------------
# 🌐 啟動事件
# -----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    log.info("🚀 伺服器啟動中...")

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        log.warning("⚠️ 沒偵測到 OPENAI_API_KEY，將使用離線回覆模式。")
    else:
        log.info("🔑 OpenAI 金鑰載入成功。")

    init_memory_system()
    await asyncio.to_thread(retry_upload)
    await asyncio.to_thread(schedule_retry_upload, 600)
    log.info("✅ 初始化完成（記憶 + 上傳系統 + 保活）")

# -----------------------------------------------------
# 🌍 CORS 設定
# -----------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# 📦 PostgreSQL 設定
# -----------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is not set")

if not DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")

if "sslmode" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"options": "-c timezone=UTC"},
    future=True
)

metadata = MetaData()

# -----------------------------------------------------
# 🗂️ Table 定義
# -----------------------------------------------------
conversations = Table(
    "conversations", metadata,
    Column("project_id", String, primary_key=True),
    Column("data", JSONB),
)

messages = Table(
    "messages", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String, index=True),
    Column("role", String),
    Column("text", Text),
    Column("tone", String),
    Column("extra", JSONB, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
)

memories = Table(
    "memories", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String, index=True),
    Column("content", Text),
    Column("tags", JSONB, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
)

metadata.create_all(engine)

# -----------------------------------------------------
# 🧱 資料模型
# -----------------------------------------------------
class Message(BaseModel):
    role: str
    text: str

class Conversation(BaseModel):
    summary: Optional[str] = None
    tone_tags: Optional[List[str]] = []
    topic_tags: Optional[List[str]] = []
    tail_messages: Optional[List[Message]] = []

class MessageIn(BaseModel):
    role: str
    text: str
    extra: Optional[dict] = None

class MemoryIn(BaseModel):
    content: str
    tags: Optional[List[str]] = []

class MemoryImportIn(BaseModel):
    items: List[MemoryIn]

# -----------------------------------------------------
# ❤️ Health Check
# -----------------------------------------------------
@app.get("/")
def health():
    return {"ok": True, "app": "chat-context"}

# -----------------------------------------------------
# 🧠 Tone Engine 高性能人格回覆
# -----------------------------------------------------
@app.post("/auto-reply")
async def auto_reply(user_input: str):
    response = await generate_ai_reply(user_input)
    return {
        "reply": response["reply"],
        "engine": response["engine"],
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "online" if response["engine"] != "offline" else "offline",
    }

# -----------------------------------------------------
# 💓 智慧保活 + 睡眠偵測 + 平滑恢復
# -----------------------------------------------------
last_activity = datetime.utcnow()

@app.middleware("http")
async def update_last_activity(request, call_next):
    global last_activity
    response = await call_next(request)
    last_activity = datetime.utcnow()
    return response

def smart_keep_alive():
    url = "https://heavyweight-fastapi-production-b71c.up.railway.app/ping"
    log.info("💡 Smart Keep-Alive 已啟動")
    while True:
        try:
            idle_seconds = (datetime.utcnow() - last_activity).total_seconds()
            interval = 60 if idle_seconds < 300 else 180 if idle_seconds < 1800 else 600
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                log.info(f"💤 [保活] 成功（間隔 {interval}s）")
            else:
                log.warning(f"⚠️ [保活] 回傳非 200：{r.status_code}")
        except Exception:
            log.exception("⚠️ [保活] 連線失敗")
        time.sleep(interval)

@app.on_event("startup")
def start_smart_keep_alive():
    threading.Thread(target=smart_keep_alive, daemon=True).start()

def cloud_sleep_watcher():
    log.info("🌙 Sleep Watcher 已啟動（雲端記憶保護中）")
    low_activity_time = 0
    while True:
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            idle_seconds = (datetime.utcnow() - last_activity).total_seconds()
            if cpu_usage < 5 and idle_seconds > 1200:
                low_activity_time += 60
            else:
                low_activity_time = 0
            if low_activity_time >= 300:
                tone_state = load_tone_state()
                personality = load_personality()
                save_personality(personality)
                log.info("💾 [SleepWatcher] 已自動保存記憶與人格狀態。")
                low_activity_time = 0
        except Exception:
            log.exception("⚠️ [SleepWatcher] 發生錯誤")
        time.sleep(60)

@app.on_event("startup")
def start_sleep_watcher():
    threading.Thread(target=cloud_sleep_watcher, daemon=True).start()

def smooth_restore(personality: dict, tone: str):
    stability = personality.get("stability", 0.7)
    core_tone = personality.get("core_tone", "calm")
    mood_map = {"angry": -0.3, "sad": -0.2, "curious": +0.1, "positive": +0.2, "neutral": 0}
    new_stability = min(max(stability + mood_map.get(tone, 0) * 0.3, 0.3), 1.0)
    if random.random() > new_stability:
        new_core = random.choice(["calm", "warm", "introspective", "analytical"])
        log.info(f"🌀 [人格過渡] {core_tone} → {new_core}")
        personality["core_tone"] = new_core
    personality["stability"] = round(new_stability, 2)
    save_personality(personality)
    log.info(f"🌄 [平滑恢復] 穩定度：{new_stability:.2f}")

@app.on_event("startup")
def startup_smooth_personality():
    def run():
        tone_path = "buffer/last_tone_state.json"
        personality_path = "buffer/last_personality_state.json"
        if os.path.exists(tone_path) and os.path.exists(personality_path):
            try:
                with open(tone_path, "r", encoding="utf-8") as tf, open(personality_path, "r", encoding="utf-8") as pf:
                    tone = json.load(tf).get("tone", "neutral")
                    personality = json.load(pf)
                    smooth_restore(personality, tone)
            except Exception:
                log.exception("⚠️ [平滑恢復] 失敗")
        else:
            log.info("💤 [平滑恢復] 找不到記憶檔案，跳過恢復。")
    threading.Thread(target=run, daemon=True).start()

# -----------------------------------------------------
# 🧠 自動備份 + 啟動還原系統
# -----------------------------------------------------
BACKUP_DIR = "buffer/backup"
os.makedirs(BACKUP_DIR, exist_ok=True)

def auto_backup_system():
    log.info("🧠 自動備份系統啟動中...")
    while True:
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            files_to_backup = [
                "buffer/personality_state.json",
                "buffer/conversation_memory.json",
                "buffer/tone_state.json"
            ]

            for f in files_to_backup:
                if os.path.exists(f):
                    backup_name = os.path.join(BACKUP_DIR, f"{os.path.basename(f)}.{timestamp}.bak")
                    shutil.copy2(f, backup_name)
                    log.info(f"💾 已備份：{backup_name}")

            backups = sorted(glob(os.path.join(BACKUP_DIR, "*.bak")), key=os.path.getmtime, reverse=True)
            for old in backups[10:]:
                os.remove(old)
                log.info(f"🗑️ 已刪除過期備份：{old}")

        except Exception:
            log.exception("⚠️ [自動備份系統] 發生錯誤")

        time.sleep(6 * 3600)  # 每 6 小時執行一次

@app.on_event("startup")
def start_auto_backup():
    threading.Thread(target=auto_backup_system, daemon=True).start()

def restore_latest_backup():
    log.info("🪄 嘗試從最近備份還原狀態...")
    try:
        latest_backups = sorted(glob(os.path.join(BACKUP_DIR, "*.bak")), key=os.path.getmtime, reverse=True)
        for bak in latest_backups:
            original_name = bak.replace(".bak", "").replace(f"{BACKUP_DIR}/", "buffer/")
            if not os.path.exists(original_name):
                shutil.copy2(bak, original_name)
                log.info(f"✅ 已從備份還原：{original_name}")
    except Exception:
        log.exception("⚠️ [備份還原] 發生錯誤")

@app.on_event("startup")
def startup_restore_backup():
    threading.Thread(target=restore_latest_backup, daemon=True).start()




