# utils/personality.py
import json
import os
from collections import deque, Counter

STATE_FILE = "buffer/personality_state.json"

# 記錄最近的語氣狀態（短期情緒記憶）
tone_history = deque(maxlen=10)

# 初始人格基調
default_personality = {
    "core_tone": "calm",
    "stability": 0.7,  # 越高代表越難被短期情緒改變
}

def load_personality():
    """讀取目前人格狀態"""
    if not os.path.exists(STATE_FILE):
        return default_personality
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_personality(state):
    """儲存人格狀態"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"💾 已更新人格基調：{state['core_tone']}（穩定度：{state['stability']}）")

def update_personality(tone: str):
    """
    根據最新語氣更新人格傾向。
    """
    tone_history.append(tone)
    counts = Counter(tone_history)
    most_common = counts.most_common(1)[0][0]

    state = load_personality()

    # 若短期情緒與基調不同，微調穩定性
    if most_common != state["core_tone"]:
        state["stability"] -= 0.05
        if state["stability"] < 0.4:
            state["core_tone"] = most_common
            state["stability"] = 0.7
            print(f"🌙 人格基調轉移 → {state['core_tone']}")
    else:
        # 維持一致時逐漸回穩
        state["stability"] = min(state["stability"] + 0.02, 0.9)

    save_personality(state)
    return state
