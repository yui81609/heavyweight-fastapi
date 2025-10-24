# utils/tone_engine.py
import asyncio
from utils.tone_detector import detect_tone
from utils.tone_memory import save_tone_state, load_tone_state, transition_tone
from utils.personality import update_personality
from utils.tone_handler import tone_delay
from utils.tone_resonance import generate_resonant_reply


class ToneEngine:
    """
    🌌 ToneEngine
    ===
    「Chat Universe」的情緒與人格核心引擎。
    
    功能：
    - 自動偵測語氣（tone）
    - 管理情緒記憶（漸變、保存）
    - 動態更新人格基調
    - 生成具「語氣共振」的回覆
    """

    def __init__(self):
        self.current_tone = "default"
        self.previous_tone = "default"
        self.core_tone = "calm"
        self.personality_state = {"core_tone": "calm"}

    async def reply(self, text: str) -> dict:
        """
        🪶 主回覆流程（非同步模式）
        模擬人性反應時間，回傳包含語氣與人格資訊的結果。
        """
        # 1️⃣ 偵測語氣
        tone = detect_tone(text)
        self.previous_tone = load_tone_state()

        # 2️⃣ 情緒漸變處理
        if tone == self.previous_tone:
            tone = transition_tone(tone)
        else:
            save_tone_state(tone)
        self.current_tone = tone

        # 3️⃣ 人格更新
        self.personality_state = update_personality(tone)
        self.core_tone = self.personality_state["core_tone"]

        # 4️⃣ 模擬回應延遲（自然語氣節奏）
        await asyncio.to_thread(tone_delay, self.core_tone)

        # 5️⃣ 生成語氣共振回覆
        reply_text = generate_resonant_reply(text, tone, self.core_tone)

        # 6️⃣ 結構化輸出
        return {
            "reply": reply_text,
            "tone": tone,
            "core_tone": self.core_tone,
            "previous_tone": self.previous_tone
        }

    # 🩶 方便除錯用的快速同步版本
    def quick_reply(self, text: str) -> str:
        result = asyncio.run(self.reply(text))
        return result["reply"]
