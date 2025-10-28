# app/main.py
from fastapi import FastAPI
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


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/save-identity")
def save_identity(req: SaveIdentityRequest):
    """
    手動把一段"長期記憶"丟進去：
    例如:
    key_terms = ["打基礎期","爸媽安心","flare 日"]
    snippet   = "我不追求一天爆衝了不起，我只想半年後我每天還能站起來，爸媽不用擔心。"
    note      = "他的長期自我描述"
    """
    save_identity_snippet(req.key_terms, req.snippet, req.note or "")
    return {"stored": True}


@app.post("/auto-reply", response_model=AutoReplyResponse)
def auto_reply(req: AutoReplyRequest):
    user_msg = req.user_message

    # 1. 抓長期記憶 (identity)
    lt_snippets = load_relevant_identity_snippets(user_msg)

    # 2. 抓近期對話summary (conversation)
    recent_chunks = load_recent_conversation_chunks(RECENT_CHUNKS_FOR_CONTEXT)

    # 3. 產生回覆
    reply = generate_reply(
        long_term_snippets=lt_snippets,
        recent_context_chunks=recent_chunks,
        user_message=user_msg,
    )

    # 4. 存 raw_log
    append_raw_log(user_msg, reply)

    # 5. 可能產生新的summary chunk (每到一個window就壓縮最近那段)
    maybe_generate_new_summary()

    # 6. 可能把這句話丟到 pending_identity 候選
    # 如果這句是在定義他自己，就丟候選
    triggers = ["我就是", "我現在要的", "我真的想成為", "我不想再", "對我來說最重要的是"]
    if any(t in user_msg for t in triggers):
        queue_identity_candidate(user_msg)

    return AutoReplyResponse(reply=reply)
