# app/main.py
from typing import List, Optional
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlalchemy import create_engine, MetaData, Table, Column, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

# -------------------- FastAPI & CORS --------------------
app = FastAPI()
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

# Railway 內網通常不需要 SSL；若你未來用外網 URL，可保留這段自動補 sslmode
if "sslmode" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
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

