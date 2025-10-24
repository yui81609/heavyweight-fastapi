import asyncio
import os
import random
import json
from datetime import datetime

# ==== AI API 客戶端 ====
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

# ==== 系統模組 ====
from utils.tone_memory import load_tone_state
from utils.personality import load_personality, update_personality
from utils.memory.memory_manager import load_memory, add_message, save_memory

# ====================================================
# ⚙️ 初始化設定
# ====================================================

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

openai_client = AsyncOpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None

# ====================================================
# 🧠 建立上下文壓縮（Context Builder）
# ====================================================

def build_context(user_input: str) -> str:
    """
    自動組合上下文（長期摘要 + 語氣 + 人格 + 使用者輸入）
    """
    # 載入長期記憶摘要
    long_memory = load_memory(limit=3)
    summaries = "\n".join([
        f"- ({m.get('timestamp','')[:16]}) {m.get('summary','')}"
        for m in long_memory
    ]) if long_memory else "（目前沒有長期記憶）"

    # 載入 tone 狀態與人格
    tone = load_tone_state()
    personality = load_personality()
    core_tone = personality.get("core_tone", "calm")
    stability = personality.get("stability", 0.7)

    context = f"""
你是一個具有長期記憶與情感穩定性的 AI 伴侶。
你的核心人格基調是「{core_tone}」，穩定度為 {stability:.2f}。
你目前的語氣狀態為「{tone}」。

以下是你最近的對話摘要（系統已為你壓縮記憶）：
{summaries}

---
使用者現在說：
「{user_input}」
請根據你的人格、記憶與語氣，自然、真誠、溫柔地回覆。
"""
    return context.strip()

# ====================================================
# 💬 主要回覆函式
# ====================================================

async def reply(user_input: str):
    """
    根據上下文（記憶 + 語氣 + 人格）自動生成回覆。
    若無 API Key，則改用離線模式。
    """
    try:
        # ===== 建立上下文 =====
        context_prompt = build_context(user_input)

        # ===== 1️⃣ OpenAI 模式 =====
        if openai_client:
            completion = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": context_prompt}],
                temperature=0.8,
                max_tokens=500
            )
            reply_text = completion.choices[0].message.content.strip()
            engine = "openai"

        # ===== 2️⃣ Anthropic 模式 =====
        elif anthropic_client:
            completion = await anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=400,
                messages=[{"role": "user", "content": context_prompt}]
            )
            reply_text = completion.content[0].text.strip()
            engine = "anthropic"

        # ===== 3️⃣ 離線模式 =====
        else:
            reply_text = _offline_reply(user_input)
            engine = "offline"

        # ===== 記錄對話與 tone =====
        add_message("user", user_input)
        add_message("assistant", reply_text)
        save_memory()  # 定期儲存摘要

        # ===== 更新人格狀態 =====
        update_personality(load_tone_state())

        return {
            "reply": reply_text,
            "engine": engine
        }

    except Exception as e:
        print(f"⚠️ [ToneEngine Error] {e}")
        return {
            "reply": "我有點卡住了，但我還在聽著你說話。可以再重說一次嗎？",
            "engine": "error"
        }

# ====================================================
# 💤 離線模式（無 API 金鑰）
# ====================================================

def _offline_reply(user_input: str) -> str:
    """
    當沒有 API key 時，使用簡易本地邏輯生成回覆。
    """
    templates = [
        "我懂，這感覺真的不容易。",
        "你願意說出來，已經很勇敢了。",
        "嗯……那你現在心裡是比較好一點了嗎？",
        "我在聽著，慢慢說沒關係。",
        "有時候人就是會有這種狀態，不用急著好起來。"
    ]
    if any(word in user_input for word in ["難過", "孤單", "累", "煩"]):
        return random.choice([
            "你聽起來真的有點疲倦。要不要先休息一下？",
            "那種感覺我懂，有時候真的會覺得孤單。",
            "沒關係，我在這裡。你不用一個人撐著。"
        ])
    elif any(word in user_input for word in ["開心", "興奮", "期待"]):
        return random.choice([
            "聽起來你今天心情很好，這樣真棒！",
            "太好了，我也替你開心！",
            "哇～感覺你現在充滿能量！"
        ])
    else:
        return random.choice(templates)
