"""
文件名: chunker.py
描述: 文档分块服务。
主要功能:
    - 按 token 数进行分块与重叠切分。
    - 生成分块文本与元数据。
依赖: 标准库
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# ============================================
# region 数据结构
# ============================================


@dataclass(frozen=True)
class Chunk:
    """文档分块结果。"""

    chunk_index: int
    text: str
    metadata: Dict[str, Any]


# endregion
# ============================================

# ============================================
# region 分块实现
# ============================================


def _simple_tokenize(text: str) -> List[str]:
    """
    简单分词：按空白切分。

    参数:
        text: 输入文本。
    返回:
        token 列表。
    """
    return [token for token in text.split() if token]


def _simple_detokenize(tokens: List[str]) -> str:
    """
    简单合并 token。

    参数:
        tokens: token 列表。
    返回:
        合并后的文本。
    """
    return " ".join(tokens)


def split_text_into_chunks(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
    tokenizer: Optional[Callable[[str], List[str]]] = None,
    detokenizer: Optional[Callable[[List[str]], str]] = None,
    base_metadata: Optional[Dict[str, Any]] = None,
) -> List[Chunk]:
    """
    将文本分块为多个 chunk。

    参数:
        text: 输入文本。
        chunk_size: 每个 chunk 的 token 数。
        overlap: 相邻 chunk 的重叠 token 数。
        tokenizer: 可选分词函数。
        detokenizer: 可选合并函数。
        base_metadata: 基础元数据。
    返回:
        Chunk 列表。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须在 [0, chunk_size) 范围内")

    tokenize = tokenizer or _simple_tokenize
    detok = detokenizer or _simple_detokenize
    tokens = tokenize(text)
    if not tokens:
        return []

    chunks: List[Chunk] = []
    start = 0
    index = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = detok(chunk_tokens)
        metadata = dict(base_metadata or {})
        metadata.update(
            {
                "chunk_index": index,
                "token_start": start,
                "token_end": end,
            }
        )
        chunks.append(Chunk(chunk_index=index, text=chunk_text, metadata=metadata))
        if end == len(tokens):
            break
        start = end - overlap
        index += 1
    return chunks


# endregion
# ============================================
