# utils/tone_handler.py
import asyncio
import random
from utils.tone_detector import detect_tone
from utils.tone_memory import save_tone_state, load_tone_state, transition_tone
from utils.personality import update_personality
from utils.tone_engine_async import ToneEngine

# 初始化 Tone 引擎
tone_engine = ToneEngine()

# -----------------------------------------------------------
# ⏳ Tone 回應延遲模擬
# -----------------------------------------------------------
TONE_DELAY_MAP = {
    "angry": (0.3, 1.0),
    "sad": (0.8, 1.5),
    "curious": (0.4, 0.9),
    "positive": (0.2, 0.6),
    "neutral": (0.5, 1.0),
    "default": (0.5, 1.0),
}

def tone_delay(tone: str):
    """根據語氣模擬不同延遲"""
    import time
    delay_range = TONE_DELAY_MAP.get(tone, TONE_DELAY_MAP["default"])
    delay = random.uniform(*delay_range)
    print(f"⌛ [{tone}] 延遲 {delay:.2f}s")
    time.sleep(delay)


# -----------------------------------------------------------
# 💬 智慧語氣回應主流程
# -----------------------------------------------------------
async def auto_soft_response(text: str) -> str:
    """
    核心流程：
    1️⃣ 偵測語氣
    2️⃣ 與上次語氣比對 → 若重複則平滑轉換
    3️⃣ 更新人格狀態（穩定度影響人格 tone）
    4️⃣ 呼叫 ToneEngine 產生語氣回覆
    5️⃣ 模擬回覆延遲
    """
    # --- 1️⃣ 偵測目前 tone
    tone = detect_tone(text)
    prev_tone = load_tone_state()

    # --- 2️⃣ 平滑轉換或記錄
    if tone == prev_tone:
        tone = transition_tone(tone)
    else:
        save_tone_state(tone)

    # --- 3️⃣ 更新人格（非同步，不阻塞主流程）
    new_personality = await update_personality(tone)

    # --- 4️⃣ 產生 ToneEngine 回覆（結合人格狀態）
    prompt = f"[人格基調: {new_personality['core_tone']} / 穩定度: {new_personality['stability']:.2f}] 使用者說：{text}"
    reply_data = await tone_engine.reply(prompt)
    reply = reply_data["reply"]

    # --- 5️⃣ 模擬延遲
    tone_delay(tone)

    print(f"🪶 回覆 tone={tone}, 人格={new_personality['core_tone']}")
    return reply


# -----------------------------------------------------------
# ✨ 測試用入口（可在本地執行測試）
# -----------------------------------------------------------
if __name__ == "__main__":
    async def test():
        test_inputs = [
            "謝謝你今天陪我聊天",
            "我覺得有點難過",
            "你覺得我該怎麼辦？",
            "真的太煩了，我快受不了了",
        ]
        for msg in test_inputs:
            response = await auto_soft_response(msg)
            print(f"\n👤 User: {msg}\n🤖 Bot: {response}\n")

    asyncio.run(test())

