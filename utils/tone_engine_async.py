# utils/tone_engine_async.py
import asyncio
import random
from collections import deque
from utils.tone_detector import detect_tone
from utils.tone_memory import save_tone_state, load_tone_state, transition_tone
from utils.personality import update_personality
from utils.tone_resonance import generate_resonant_reply

# --------------------------------------
# 🕊️ 非阻塞延遲（async）
# --------------------------------------
TONE_DELAY_MAP = {
    "calm": (0.8, 1.5),
    "relaxed": (0.5, 1.2),
    "reflective": (1.0, 2.2),
    "deep": (1.5, 2.8),
    "sad": (1.8, 3.5),
    "light": (0.3, 0.9),
    "default": (0.6, 1.4),
}

async def tone_delay_async(tone: str = "default"):
    delay_range = TONE_DELAY_MAP.get(tone, TONE_DELAY_MAP["default"])
    delay = random.uniform(*delay_range)
    print(f"🌿 [非阻塞延遲] 語氣: {tone} → 延遲 {delay:.2f} 秒")
    await asyncio.sleep(delay)

# --------------------------------------
# 🧠 Tone Engine 非同步高性能版
# --------------------------------------
class ToneEngine:
    """
    🌙 高性能 ToneEngine
    - async 全流程（不卡）
    - 限制緩衝長度（最多記錄30輪）
    - 批次寫入人格狀態（背景自動保存）
    """
    def __init__(self):
        self.current_tone = "default"
        self.previous_tone = "default"
        self.core_tone = "calm"
        self.personality_state = {"core_tone": "calm"}
        self.history = deque(maxlen=30)
        self._save_task = None

    async def reply(self, text: str) -> dict:
        # 偵測語氣
        tone = detect_tone(text)
        self.previous_tone = load_tone_state()

        # 語氣漸變
        if tone == self.previous_tone:
            tone = transition_tone(tone)
        else:
            save_tone_state(tone)
        self.current_tone = tone

        # 更新人格
        self.personality_state = update_personality(tone)
        self.core_tone = self.personality_state["core_tone"]

        # 模擬延遲（async）
        await tone_delay_async(self.core_tone)

        # 共振生成
        reply_text = generate_resonant_reply(text, tone, self.core_tone)

        # 記錄最近對話
        self.history.append({
            "user": text,
            "reply": reply_text,
            "tone": tone,
            "core_tone": self.core_tone
        })

        # 啟動背景儲存任務
        if not self._save_task or self._save_task.done():
            self._save_task = asyncio.create_task(self._save_personality())

        return {
            "reply": reply_text,
            "tone": tone,
            "core_tone": self.core_tone
        }

    async def _save_personality(self):
        """背景儲存任務（批次寫入）"""
        await asyncio.sleep(5)
        from utils.personality import save_personality
        save_personality(self.personality_state)
        print("💾 批次儲存人格狀態完成。")

    # 同步快速測試
    def quick_reply(self, text: str) -> str:
        return asyncio.run(self.reply(text))["reply"]


from utils.background_cleaner import periodic_cleanup
import threading

class ToneEngine:
    def __init__(self):
        self.current_tone = "default"
        self.previous_tone = "default"
        self.core_tone = "calm"
        self.personality_state = {"core_tone": "calm"}
        self.history = deque(maxlen=30)
        self._save_task = None

        # ✅ 啟動背景清理執行緒
        threading.Thread(
            target=periodic_cleanup,
            args=(3,),   # 每 3 小時執行一次
            daemon=True
        ).start()
        print("🧹 背景清理器啟動完成（每3小時運行一次）")

