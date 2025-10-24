# app/main.py
from utils.uploader import safe_upload, retry_upload
from typing import List, Optional
import os, asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, String, select
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert

# ---------------- FastAPI & CORS ----------------
app = FastAPI(
    title="Heavyweight FastAPI",
    version="1.0.0",
    servers=[{"url": "https://heavyweight-fastapi-production-b71c.up.railway.app"}]
)

@app.on_event("startup")
async def startup_event():
    print("🚀 伺服器啟動，檢查暫存上傳中...")
    await asyncio.to_thread(retry_upload)  # 使用非同步執行，避免阻塞主線程

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -------------------- Pydantic Models --------------------
class Message(BaseModel):
    role: str
    text: str

class Conversation(BaseModel):
    summary: Optional[str] = None
    tone_tags: Optional[List[str]] = []
    topic_tags: Optional[List[str]] = []
    tail_messages: Optional[List[Message]] = []

# -------------------- Health --------------------
@app.get("/")
def health():
    return {"ok": True, "app": "chat-context"}

# -------------------- PostgreSQL (SQLAlchemy) --------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# ⚠️ 強制指定 psycopg 驅動
if not DATABASE_URL.startswith("postgresql+psycopg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")


# Railway 內網通常不需要 SSL；若你未來用外網 URL，可保留這段自動補 sslmode
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

conversations = Table(
    "conversations",
    metadata,
    Column("project_id", String, primary_key=True),
    Column("data", JSONB),  # 直接存整包 JSON
)

# 啟動時建表（若不存在）
metadata.create_all(engine)

def _default_conv():
    return {"summary": None, "tone_tags": [], "topic_tags": [], "tail_messages": []}

# -------------------- API: 讀取最後一次對話 --------------------
@app.get("/projects/{project_id}/last-conversation")
def get_last_conversation(project_id: str):
    with engine.begin() as conn:
        row = conn.execute(
            select(conversations.c.data).where(conversations.c.project_id == project_id)
        ).fetchone()
    return row[0] if row else _default_conv()

# -------------------- API: 儲存/覆蓋對話 --------------------
@app.post("/projects/{project_id}/save-conversation")
def save_conversation(project_id: str, conv: Conversation):
    payload = conv.dict()
    with engine.begin() as conn:
        stmt = pg_insert(conversations).values(project_id=project_id, data=payload)
        # 若主鍵衝突（同一 project_id），改成更新
        stmt = stmt.on_conflict_do_update(
            index_elements=[conversations.c.project_id],
            set_={"data": stmt.excluded.data},
        )
        conn.execute(stmt)
    return {"ok": True, "conversation_id": 1}
# ==== 追加在你現有 app/main.py 的底部（保留前面的 import 與 engine/metadata） ====
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import insert, func

# ---------- 簡易語氣分析器（可之後換更聰明的） ----------
def detect_tone(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["thank", "thanks", "感謝", "謝謝"]):
        return "positive"
    if any(k in t for k in ["angry", "annoy", "氣", "生氣"]):
        return "angry"
    if any(k in t for k in ["sad", "down", "難過", "傷心"]):
        return "sad"
    if any(k in t for k in ["?", "？"]):
        return "curious"
    return "neutral"

# ---------- 資料表：messages（單則訊息＋語氣） ----------
messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String, index=True),
    Column("role", String),          # "user" / "assistant"
    Column("text", Text),
    Column("tone", String),          # 自動分析結果
    Column("extra", JSONB, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
)

# ---------- 資料表：memories（個人記憶） ----------
memories = Table(
    "memories",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", String, index=True),
    Column("content", Text),         # 記憶內容
    Column("tags", JSONB, nullable=True),  # 例如 ["自律","價值觀"]
    Column("created_at", DateTime, server_default=func.now()),
)

metadata.create_all(engine)

# ---------- Pydantic 輸入模型 ----------
class MessageIn(BaseModel):
    role: str
    text: str
    extra: Optional[dict] = None

class MemoryIn(BaseModel):
    content: str
    tags: Optional[List[str]] = []

class MemoryImportIn(BaseModel):
    items: List[MemoryIn]

# ========== 1) 寫入一則訊息，並自動分析語氣 ==========
@app.post("/projects/{project_id}/messages")
def save_message(project_id: str, msg: MessageIn):
    tone = detect_tone(msg.text)
    with engine.begin() as conn:
        conn.execute(
            messages.insert().values(
                project_id=project_id,
                role=msg.role,
                text=msg.text,
                tone=tone,
                extra=msg.extra or {},
            )
        )
    return {"ok": True, "tone": tone}

# ========== 2) 語氣統計（最近 100 則） ==========
@app.get("/projects/{project_id}/tone-stats")
def tone_stats(project_id: str, limit: int = 100):
    with engine.begin() as conn:
        rows = conn.execute(
            select(messages.c.tone).where(messages.c.project_id == project_id)
            .order_by(messages.c.created_at.desc())
            .limit(limit)
        ).fetchall()
    from collections import Counter
    counts = Counter([r[0] for r in rows])
    total = sum(counts.values()) or 1
    return {
        "ok": True,
        "samples": len(rows),
        "distribution": {k: v for k, v in counts.items()},
        "ratio": {k: v / total for k, v in counts.items()},
    }

# ========== 3) 新增個人記憶 ==========
@app.post("/projects/{project_id}/memories")
def add_memory(project_id: str, mem: MemoryIn):
    with engine.begin() as conn:
        conn.execute(
            memories.insert().values(
                project_id=project_id,
                content=mem.content,
                tags=mem.tags or [],
            )
        )
    return {"ok": True}

# ========== 4) 列出 / 搜尋個人記憶 ==========
@app.get("/projects/{project_id}/memories")
def list_memories(project_id: str, q: Optional[str] = None, limit: int = 50):
    with engine.begin() as conn:
        stmt = select(
            memories.c.id, memories.c.content, memories.c.tags, memories.c.created_at
        ).where(memories.c.project_id == project_id).order_by(memories.c.created_at.desc()).limit(limit)
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

# ========== 5) 批次匯入個人記憶 ==========
@app.post("/projects/{project_id}/memories/import")
def import_memories(project_id: str, payload: MemoryImportIn):
    items = payload.items or []
    with engine.begin() as conn:
        for it in items:
            conn.execute(
                memories.insert().values(
                    project_id=project_id,
                    content=it.content,
                    tags=it.tags or [],
                )
            )
    return {"ok": True, "imported": len(items)}

