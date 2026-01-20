"""
文件名: reranker.py
描述: 重排服务占位实现。
主要功能:
    - 将查询与候选文本进行重排打分。
依赖: 无
"""

from __future__ import annotations

from typing import List

# ============================================
# region 重排接口
# ============================================


def rerank_texts(query: str, candidates: List[str]) -> List[float]:
    """
    重排打分（占位实现）。

    参数:
        query: 查询文本。
        candidates: 候选文本列表。
    返回:
        分数列表（与候选数量一致）。
    """
    raise NotImplementedError("rerank 服务未实现")


def set_reranker(reranker: Callable[[str, List[str]], List[float]]) -> None:
    """
    设置全局 rerank 实现（用于测试或替换实现）。

    参数:
        reranker: rerank 函数。
    """
    global rerank_texts
    rerank_texts = reranker


# endregion
# ============================================
