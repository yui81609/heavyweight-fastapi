# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import AutoReplyRequest, AutoReplyResponse, SaveIdentityRequest
from app.memory import (
    load_relevant_identity_snippets,
    load_recent_conversation_chunks,
    append_raw_log,
    maybe_generate_new_summary,
    save_identity_snippet,
    queue_identity_candidate,
)
from app.llm_client import generate_reply
from app.config import RECENT_CHUNKS_FOR_CONTEXT

app = FastAPI(
    title="Heavyweight FastAPI",
    version="3.0.0",
)

# 如果你前端會從別的 domain call，就留著 CORS 全開；沒特別需要其實也可以拿掉
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 之後你可以鎖你自己的網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # 確認服務可以正常起來
    return {"ok": True}


@app.post("/save-identity")
def save_identity(req: SaveIdentityRequest):
    """
    手動把一段「長期記憶」寫進去。
    例如：
        {
          "key_terms": ["打基礎期","爸媽安心","flare 日","長期站著"],
          "snippet": "我不是要一天爆衝很猛，我是要半年後還能每天起來，自己調整狀態，爸媽能安心。",
          "note": "他的長期自我定義"
        }
    這些會進 identity_memory.jsonl
    """
    save_identity_snippet(req.key_terms, req.snippet, req.note or "")
    return {"stored": True}


@app.post("/auto-reply", response_model=AutoReplyResponse)
def auto_reply(req: AutoReplyRequest):
    """
    產生回覆的主流程：
    1. 用 user_message 去找長期記憶中有關的片段 (identity_memory.jsonl)
    2. 把最近幾段 conversation summary 抓出來 (conversation_memory.jsonl)
    3. 丟給模型 + 我們固定的 system prompt，產生回覆
    4. 把這輪 user / reply 寫進 raw_log.jsonl
    5. 如果累積到一定數量，就自動做一段新的 summary（就是分層短期記憶）
    6. 如果 user_message 是「自我定義式的話」，就丟到 pending_identity.jsonl 等你人工升級
    """
    user_msg = req.user_message

