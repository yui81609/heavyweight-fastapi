import random
import time
from utils.tone_detector import detect_tone
from utils.tone_memory import save_tone_state, load_tone_state, transition_tone
from utils.personality import update_personality
from utils.tone_resonance import generate_resonant_reply

# --------------------------------
# 🕊️ Tone 延遲設定
# --------------------------------
TONE_DELAY_MAP = {
    "calm": (0.8, 1.5),
    "relaxed": (0.5, 1.2),
    "reflective": (1.0, 2.2),
    "deep": (1.5, 2.8),
    "sad": (1.8, 3.5),
    "light": (0.3, 0.9),
    "default": (0.6, 1.4)
}

def tone_delay(tone: str = "default"):
    """
    根據語氣決定回應延遲，模擬「呼吸感」
    """
    delay_range = TONE_DELAY_MAP.get(tone, TONE_DELAY_MAP["default"])
    delay = random.uniform(*delay_range)
    print(f"🌿 [安靜模式] 語氣: {tone} → 延遲 {delay:.2f} 秒")
    time.sleep(delay)


# --------------------------------
# 💬 基礎層：柔和延遲回覆
# --------------------------------
def soft_response(text: str, tone: str = "default") -> str:
    """
    🕊️ 模擬柔和回應：根據 tone 延遲後回傳文字
    用於靜態回覆或固定語氣（不含情緒偵測邏輯）
    """
    tone_delay(tone)
    return text


# --------------------------------
# 🌙 高階層：自動語氣回應主流程
# --------------------------------
def auto_soft_response(text: str):
    """
    🌙 自動語氣回應核心函式：
    - 偵測語氣（tone）
    - 比對上次情緒，啟動漸變機制
    - 更新人格基調
    - 套用人格語氣共振回覆
    - 模擬自然延遲
    """
    # 1️⃣ 偵測語氣 + 載入上次 tone
    tone = detect_tone(text)
    previous_tone = load_tone_state()

    # 2️⃣ 若語氣與上輪相同 → 啟動情緒漸變
    if tone == previous_tone:
        tone = transition_tone(tone)
    else:
        save_tone_state(tone)

    # 3️⃣ 更新人格平衡狀態
    personality_state = update_personality(tone)
    core_tone = personality_state["core_tone"]

    # 4️⃣ 模擬自然延遲（根據人格基調）
    tone_delay(core_tone)

    # 5️⃣ 語氣共振生成回覆
    reply = generate_resonant_reply(text, tone, core_tone)

    # 6️⃣ 回傳完整資訊（便於記錄與測試）
    return {
        "reply": reply,
        "tone": tone,
        "core_tone": core_tone,
        "previous_tone": previous_tone
    }

