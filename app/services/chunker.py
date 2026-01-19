"""
文件名: chunker.py
描述: 文本分块工具，按固定大小与重叠切分长文本。
主要功能:
    - 根据 chunk_size 与 overlap 切分文本
    - 过滤空块，保留顺序
依赖: app.config
"""

from typing import List

from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    将长文本切分为多个块。

    参数:
        text: 待切分文本
        chunk_size: 单块最大字符数
        chunk_overlap: 块间重叠字符数
    返回:
        文本块列表，已过滤空块
    """
    if not text or not text.strip():
        return []

    chunk_size = max(1, chunk_size)
    chunk_overlap = max(0, min(chunk_overlap, chunk_size - 1))

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - chunk_overlap

    return chunks
