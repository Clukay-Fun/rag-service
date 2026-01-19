"""
文件名: embedding.py
描述: 向量化服务，封装 SiliconFlow Embedding API 调用。
主要功能:
    - 单文本向量生成
    - 批量向量生成
依赖: httpx, app.config
"""

from typing import List, Optional

import httpx

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    EMBEDDING_MODEL,
)


# ============================================
# region 单条向量生成
# ============================================
def get_embedding(text: str) -> Optional[List[float]]:
    """
    为单条文本生成向量。

    参数:
        text: 待向量化文本
    返回:
        向量数组，失败时返回 None
    """
    if not text or not text.strip():
        return None

    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
                "encoding_format": "float",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as exc:  # pragma: no cover - 网络异常打印即可
        print(f"[embedding] get_embedding failed: {exc}")
        return None
# endregion
# ============================================


# ============================================
# region 批量向量生成
# ============================================
def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    批量生成文本向量。

    参数:
        texts: 文本列表
    返回:
        与输入一一对应的向量列表（失败处为 None）
    """
    if not texts:
        return []

    # 过滤空文本，保持索引对齐
    valid_texts = [t if t and t.strip() else "" for t in texts]

    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": valid_texts,
                "encoding_format": "float",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()
        data = sorted(result["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in data]
    except Exception as exc:  # pragma: no cover
        print(f"[embedding] get_embeddings_batch failed: {exc}")
        return [None] * len(texts)
# endregion
# ============================================
