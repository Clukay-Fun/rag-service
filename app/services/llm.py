"""
对话模型客户端：调用 SiliconFlow 接口生成回复。
"""

import httpx

from app.config import CHAT_MODEL, SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL


# ============================================
# region LLM
# ============================================
async def chat_completion(prompt: str) -> str:
    if not SILICONFLOW_API_KEY:
        return "抱歉，当前未配置对话模型，已切换为简要回复。"

    url = f"{SILICONFLOW_BASE_URL}/chat/completions"
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "你是招投标助手，请简洁回答。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code != 200:
            return "抱歉，当前对话服务不可用。"
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return "抱歉，当前对话服务不可用。"
# endregion
# ============================================
