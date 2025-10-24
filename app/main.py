# app/main.py
import os, json, asyncio
from typing import List, Optional
from collections import Counter
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, Text, Integer,
    DateTime, select, func
)
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert

from utils.uploader import safe_upload, retry_upload, schedule_retry_upload
from utils.tone_engine_async import ToneEngine

# -----------------------------------------------------
# 🚀 FastAPI 初始化
# -----------------------------------------------------
app = FastAPI(
    title="Heavyweight FastAPI",
    version="1.0.0",
    servers=[{"url": "https://heavyweight-fastapi-production-b71c.up.railway.app"}],
)

@app.on_event("startup")
async def startup_event():
    print("🚀 伺服器啟動，檢查暫存上傳中...")
    await asyncio.to_thread(retry_upload)
    await asyncio.to_thread(schedule_retry_upload, 600)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# 📦 PostgreSQL 連線設定
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
# 🧱 Pydantic Models
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
# 💬 Conversation API
# -----------------------------------------------------
def _default_conv():
    return {"summary": None, "tone_tags": [], "topic_tags": [], "tail_messages": []}

@app.get("/projects/{project_id}/last-conversation")
def get_last_conversation(project_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            select(conversations.c.data).where(conversations.c.project_id == project_id)
        ).fetchone()
    return row[0] if row else _default_conv()

@app.post("/projects/{project_id}/save-conversation")
def save_conversation(project_id: str, conv: Conversation):
    payload = conv.dict()
    with engine.begin() as conn:
        stmt = pg_insert(conversations).values(project_id=project_id, data=payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[conversations.c.project_id],
            set_={"data": stmt.excluded.data},
        )
        conn.execute(stmt)
    return {"ok": True}

# -----------------------------------------------------
# 🧠 Tone 分析（基礎）
# -----------------------------------------------------
def detect_tone(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["thank", "thanks", "感謝", "謝謝"]):
        return "positive"
    if any(k in t for k in ["angry", "氣", "生氣"]):
        return "angry"
    if any(k in t for k in ["sad", "難過", "傷心"]):
        return "sad"
    if any(k in t for k in ["?", "？"]):
        return "curious"
    return "neutral"

# -----------------------------------------------------
# 📜 Message + Memory APIs
# -----------------------------------------------------
@app.post("/projects/{project_id}/messages")
def save_message(project_id: str, msg: MessageIn):
    tone = detect_tone(msg.text)
    with engine.begin() as conn:
        conn.execute(messages.insert().values(
            project_id=project_id,
            role=msg.role,
            text=msg.text,
            tone=tone,
            extra=msg.extra or {},
        ))
    return {"ok": True, "tone": tone}

@app.get("/projects/{project_id}/tone-stats")
def tone_stats(project_id: str, limit: int = 100):
    with engine.begin() as conn:
        rows = conn.execute(
            select(messages.c.tone)
            .where(messages.c.project_id == project_id)
            .order_by(messages.c.created_at.desc())
            .limit(limit)
        ).fetchall()
    counts = Counter([r[0] for r in rows])
    total = sum(counts.values()) or 1
    return {
        "ok": True,
        "samples": len(rows),
        "distribution": counts,
        "ratio": {k: v / total for k, v in counts.items()},
    }

@app.post("/projects/{project_id}/memories")
def add_memory(project_id: str, mem: MemoryIn):
    with engine.begin() as conn:
        conn.execute(memories.insert().values(
            project_id=project_id,
            content=mem.content,
            tags=mem.tags or [],
        ))
    return {"ok": True}

@app.get("/projects/{project_id}/memories")
def list_memories(project_id: str, q: Optional[str] = None, limit: int = 50):
    with engine.begin() as conn:
        stmt = select(
            memories.c.id, memories.c.content, memories.c.tags, memories.c.created_at
        ).where(memories.c.project_id == project_id)\
         .order_by(memories.c.created_at.desc())\
         .limit(limit)
        rows = conn.execute(stmt).fetchall()

    def match(row):
        if not q:
            return True
        return (q.lower() in (row.content or "").lower()) or any(
            q.lower() in (tag or "").lower() for tag in (row.tags or [])
        )

    data = [
        {
            "id": r.id,
            "content": r.content,
            "tags": r.tags or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows if match(r)
    ]
    return {"ok": True, "items": data}

@app.post("/projects/{project_id}/memories/import")
def import_memories(project_id: str, payload: MemoryImportIn):
    items = payload.items or []
    with engine.begin() as conn:
        for it in items:
            conn.execute(memories.insert().values(
                project_id=project_id,
                content=it.content,
                tags=it.tags or [],
            ))
    return {"ok": True, "imported": len(items)}

# -----------------------------------------------------
# ⚙️ 工具：上傳重試 / 暫存查詢
# -----------------------------------------------------
BUFFER_FILE = "buffer/pending.jsonl"

@app.post("/force-retry")
async def force_retry():
    await asyncio.to_thread(retry_upload)
    return {"message": "已手動執行 retry_upload()"}

@app.get("/pending")
async def get_pending():
    if not os.path.exists(BUFFER_FILE):
        return JSONResponse({"pending": [], "message": "沒有暫存檔案"}, status_code=200)
    with open(BUFFER_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    if not lines:
        return JSONResponse({"pending": [], "message": "暫存為空"}, status_code=200)

    preview = [
        {
            "url": item.get("url", ""),
            "content": item.get("payload", {}).get("content", "")[:50],
            "tags": item.get("payload", {}).get("tags", [])
        }
        for item in lines
    ]
    return JSONResponse({"pending": preview, "count": len(preview)}, status_code=200)

# -----------------------------------------------------
# 🪶 Tone Engine 高性能人格回覆
# -----------------------------------------------------
engine_tone = ToneEngine()

@app.post("/auto-reply")
async def auto_reply(user_input: str):
    response = await engine_tone.reply(user_input)
    return {"reply": response["reply"]}


