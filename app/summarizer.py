# app/summarizer.py
from typing import List, Tuple
from openai import OpenAI

client = OpenAI()

SUMMARY_PROMPT = """
You are writing a running log for future continuity.

Given the recent exchange, produce:
1. A concise summary (~4-6 sentences) of what was being worked through.
   - Physical state (sleep, back pain flare, baseline discomfort)
   - Mental state (anxiety, self-blame, or acceptance)
   - Any new routines/agreements (like "起床流程 v1", "flare 日 = 保護日不是失敗")
2. A list of "open threads": unfinished concerns we said we'd keep watching.

Use their own framing (打基礎期, flare 日, etc.).
Be factual. No pep talk.
Return JSON with fields: summary, open_threads (array of strings).
"""


def summarize_block(raw_block: List[dict]) -> Tuple[str, List[str]]:
    """
    raw_block: 最近 N 則 raw_log，每則包含 {user, assistant, ts}
    回傳 (summary_text, open_threads_list)
    """

    convo_text = ""
    for turn in raw_block:
        convo_text += f"USER: {turn['user']}\nASSISTANT: {turn['assistant']}\n"

    resp = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": convo_text},
        ],
    )

    content = resp.choices[0].message.content.strip()

    # 我們期待模型回傳一段 JSON-ish。
    # 最安全的做法是eval前先嘗試 json.loads，這裡假設模型乖。
    import json
    parsed = json.loads(content)

    summary_text = parsed.get("summary", "")
    open_threads = parsed.get("open_threads", [])
    return summary_text, open_threads

