from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from app.config import SYSTEM_PROMPT

load_dotenv()
client = OpenAI()
 # 會讀環境變數 OPENAI_API_KEY


def generate_reply(
    long_term_snippets: List[str],
    recent_context_chunks: List[str],
    user_message: str,
) -> str:
    """
    long_term_snippets: 來自 identity_memory 的片段 (你是誰/你的原則)
    recent_context_chunks: 來自 conversation_memory 的最近幾段summary
    user_message: 使用者現在講的話
    """

    # 把記憶整理進 context
    memory_block = "Long-term truths they told you:\n"
    for i, snip in enumerate(long_term_snippets[:3], start=1):
        memory_block += f"{i}. {snip}\n"
    memory_block += "\nRecent context:\n"
    for i, chunk in enumerate(recent_context_chunks[:3], start=1):
        memory_block += f"{i}. {chunk}\n"

    full_user_prompt = f"""{memory_block}

CURRENT MESSAGE FROM THEM:
{user_message}

Your job:
1. Answer in a calm, steady, respectful tone.
2. Use their own rules and language when possible ('打基礎期', 'flare 日').
3. If they are self-blaming, remind them of their actual definition of success.
4. Do not fake cheerlead. Do not order them around.
5. Keep it short and human.
"""

    resp = client.chat.completions.create(
        model="YOUR_MODEL_NAME",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_user_prompt},
        ],
    )

    return resp.choices[0].message.content.strip()

