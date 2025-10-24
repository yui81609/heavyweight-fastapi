# utils/tone_handler.py
import time
import random

# 定義不同語氣的延遲秒數範圍
TONE_DELAY_MAP = {
    "calm": (1.5, 2.5),
    "reflective": (2.5, 3.5),
    "sad": (3.0, 4.0),
    "relaxed": (1.0, 2.0),
    "light": (0.5, 1.2),
    "deep": (2.0, 3.0),
    "default": (1.0, 2.0),
}

def tone_delay(tone: str):
    """
    根據語氣決定回覆延遲，模擬「呼吸感」
    """
    delay_range = TONE_DELAY_MAP.get(tone, TONE_DELAY_MAP["default"])
    delay = random.uniform(*delay_range)
    print(f"🕊️ [安靜模式] 語氣: {tone} → 延遲 {delay:.2f} 秒")
    time.sleep(delay)

def soft_response(text: str, tone: str = "default"):
    """
    模擬柔和回應：延遲後回傳文字
    """
    tone_delay(tone)
    return f"{text}"

from utils.tone_detector import detect_tone
from utils.tone_memory import save_tone_state, load_tone_state, transition_tone

def auto_soft_response(text: str):
      """
    自動判斷語氣 + 模擬延遲回應（會記憶上次情緒並逐步轉換）
    """
    tone = detect_tone(text)
    previous_tone = load_tone_state()
    
    # 如果當前 tone 跟上一輪相同，則啟動情緒漸變
    if tone == previous_tone:
        tone = transition_tone(tone)
    else:
        save_tone_state(tone)

    tone_delay(tone)

    return f"{text}（語氣：{tone}｜上一輪：{previous_tone}）"
