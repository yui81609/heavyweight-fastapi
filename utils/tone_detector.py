# utils/tone_detector.py
import re

# 基礎語氣關鍵詞對照表
TONE_KEYWORDS = {
    "sad": ["難過", "孤單", "失落", "不想動", "心累", "沒力氣"],
    "relaxed": ["放鬆", "舒服", "還好", "平靜", "慢慢來", "沒事"],
    "light": ["哈哈", "XD", "好啦", "還行", "開心", "可愛"],
    "reflective": ["矛盾", "自由", "意義", "存在", "焦慮", "思考"],
    "deep": ["真實", "靈魂", "命運", "時間", "選擇", "人生"],
    "calm": ["沒關係", "好吧", "嗯", "好像", "靜靜", "淡淡"],
}

def detect_tone(text: str) -> str:
    """
    根據文字內容簡易推測語氣 tone
    """
    text = text.lower()
    for tone, keywords in TONE_KEYWORDS.items():
        for word in keywords:
            if re.search(word, text):
                print(f"🎧 偵測到語氣: {tone}（觸發詞：{word}）")
                return tone
    return "default"
