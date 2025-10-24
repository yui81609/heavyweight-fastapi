# utils/tone_engine_async.py
import os
import asyncio
import json
import random
from openai import AsyncOpenAI
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 整合理解模型
from utils.personality import update_understanding, describe_personality
from utils.memory.memory_manager import add_message, save_memory_async

# 初始化 OpenAI 非同步客戶端
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 語氣分析器
analyzer = SentimentIntensityAnalyzer()


# ======================================================
# 🎧 偵測語氣
# ======================================================
def detect_tone(text: str) -> str:
    """
    使用關鍵詞與情緒分數分析 tone。
    """
    t = text.lower()
    score = analyzer.polarity_scores(text)["compound"]

    if any(k in t for k in ["謝謝", "感謝", "thank", "love", "開心"]):
        return "positive"
    if any(k in t for k in ["生氣", "氣", "angry", "不爽"]):
        return "angry"
    if any(k in t for k in ["難過", "sad", "失落", "低落"]):
        return "sad"
    if any(k in t for k in ["?", "？", "why", "為什麼"]):
        return "curious"

    if score > 0.3:
        return "positive"
    elif score < -0.3:
        return "sad"
    return "neutral"


# ======================================================
# 🧠 核心：理解型 AI 回覆
# ======================================================
async def reply(user_input: str) -> dict:
    """
    理解型 AI 回覆引擎
    - 偵測使用者語氣
    - 更新理解模型
    - 動態生成自然語氣的 GPT 回覆
    """

    # 1️⃣ 分析語氣
    tone = detect_tone(user_input)

    # 2️⃣ 更新理解模型
    personality_state = await update_understanding(tone)
    empathy_context = describe_personality()

    # 3️⃣ 根據理解模型動態調整回覆語氣
    empathy = personality_state["empathy"]
    familiarity = personality_state["familiarity"]

    if empathy > 0.8:
        style = "語氣溫柔、體貼、真誠、理解使用者的心情。"
    elif familiarity > 0.7:
        style = "語氣自然、像朋友聊天一樣輕鬆。"
    else:
        style = "語氣中立、簡潔但關心對方。"

    # 4️⃣ 組合提示詞
    prompt = f"""
你是一個能夠理解人類情緒的聊天夥伴。
請根據使用者的語氣與情緒，以 {style} 的方式回應。

目前的理解狀態：
{empathy_context}

使用者說：
「{user_input}」

請以真實、自然、貼近的語氣回覆一句話。
    """

    # 5️⃣ 調用 OpenAI GPT 模型
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=120,
        )

        ai_reply = response.choices[0].message.content.strip()

    except Exception as e:
        print(f"⚠️ OpenAI 回覆失敗：{e}")
        ai_reply = random.choice([
            "我在聽呢，慢慢說就好。",
            "我懂，有時候真的會那樣。",
            "我在這裡。"
        ])

    # 6️⃣ 記錄對話（非同步保存）
    add_message("user", user_input)
    add_message("assistant", ai_reply)
    await save_memory_async()

    # 7️⃣ 回傳結構化資料
    return {
        "reply": ai_reply,
        "tone": tone,
        "personality": personality_state,
        "engine": "openai-understanding"
    }
