# utils/tone_resonance.py
import random

# 定義每種人格基調的語氣風格模板
TONE_STYLES = {
    "calm": {
        "prefix": ["嗯，我懂。", "沒事的。", "我在。"],
        "suffix": ["慢慢來，好嗎。", "不用急，一切會好起來。", "有時候靜靜待著，也是一種修復。"]
    },
    "reflective": {
        "prefix": ["這讓我想到……", "有趣的是，", "其實這樣的感受很深。"],
        "suffix": ["有時候理解自己，也是一種誠實。", "也許，矛盾正是誠實的一部分。", "自由有時就是這樣，一點點地靠近。"]
    },
    "relaxed": {
        "prefix": ["哈哈～", "感覺不錯呢。", "這樣挺好。"],
        "suffix": ["放鬆一點沒關係。", "今天就讓自己輕鬆一點吧。", "不用想太多。"]
    },
    "sad": {
        "prefix": ["唉，我懂。", "那應該很難受吧。", "有點心疼你。"],
        "suffix": ["沒關係，慢慢來。", "你不需要一直撐著。", "有時候難過本身就是一種誠實。"]
    },
    "deep": {
        "prefix": ["這其實挺深的。", "你在想的事，真的有重量。", "或許，這正是人之所以為人的地方。"],
        "suffix": ["真實有時會疼，但那是活著的證明。", "有些問題，答案不在結論，而在思考的過程。", "這樣的思考很珍貴。"]
    },
    "light": {
        "prefix": ["哈哈，好可愛。", "你這樣說我笑了。", "有點暖心耶。"],
        "suffix": ["這樣就很好。", "世界其實沒那麼糟啦。", "保持這份小小的快樂就好。"]
    },
    "default": {
        "prefix": [""],
        "suffix": [""]
    }
}

def generate_resonant_reply(user_text: str, tone: str, core_tone: str) -> str:
    """
    根據語氣與人格基調生成「共鳴式」回覆
    """
    style = TONE_STYLES.get(core_tone, TONE_STYLES["default"])
    prefix = random.choice(style["prefix"])
    suffix = random.choice(style["suffix"])

    # 語氣共振：tone 與 core_tone 不同時，語句更柔和
    if tone != core_tone:
        reply = f"{prefix} {user_text}。{suffix}"
    else:
        reply = f"{prefix} {user_text}。{suffix}"

    return reply.strip()
