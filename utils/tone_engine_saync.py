# app/utils/tone_engine_async.py
import os
import asyncio
import random
import json
from datetime import datetime

# 嘗試載入 OpenAI 或 Anthropic SDK
try:
    import openai
except ImportError:
    openai = None

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# 載入人格與記憶模組
from utils.personality import load_personality
from utils.memory.memory_manager import load_memory

# ======================================================
# 🧩 初始化
# ======================================================
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

if OPENAI_KEY and openai:
    openai.api_key = OPENAI_KEY
    ENGINE_MODE = "openai"
elif ANTHROPIC_KEY and Anthropic:
    client = Anthropic(api_key=ANTHROPIC_KEY)
    ENGINE_MODE = "anthropic"
else:
    ENGINE_MODE = "offline"  # 沒有外部引擎就用模板模式

# ======================================================
# 💬 Prompt 組裝器
# ======================================================
def build_prompt(user_input: str) -> str:
    personality = load_personality()
    memories = load_memory(limit=3)

    memory_text = "\n".join([f"- {m['summary']}" for m in memories]) if memories else "(沒有近期記憶)"

    return f"""
你是一個具人格的 AI 朋友，能以溫柔、真實的語氣與使用者對話。

人格基調：{personality.get("core_tone")}
穩定度：{personality.get("stability")}
近期記憶：
{memory_text}

現在的對話：
使用者：「{user_input}」
請用自然語氣回覆一句真實、有情感的話。
"""

# ======================================================
# ⚙️ 主要生成函式
# ======================================================
async def generate_reply(prompt: str) -> str:
    if ENGINE_MODE == "openai":
        completion = await asyncio.to_thread(
            openai.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個懂人心、溫柔、有情感的 AI。"},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content.strip()

    elif ENGINE_MODE == "anthropic":
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )
        return response.content[0].text.strip()

    else:
        # 離線模式（沒金鑰時的模板）
        samples = [
            "嗯…這樣的感覺我好像懂，你還好嗎？",
            "哈哈，你的表達方式很特別欸。",
            "原來如此，那你現在的心情是放鬆的嗎？",
            "有點像我以前在想的事，感覺挺深的。"
        ]
        await asyncio.sleep(random.uniform(0.4, 0.8))
        return random.choice(samples)

# ======================================================
# 🧩 封裝給外部呼叫
# ======================================================
async def reply(user_input: str):
    prompt = build_prompt(user_input)
    response = await generate_reply(prompt)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "reply": response,
        "engine": ENGINE_MODE,
    }
