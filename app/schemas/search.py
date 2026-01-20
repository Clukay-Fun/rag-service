"""
文件名: search.py
描述: 检索请求与响应模型。
主要功能:
    - 定义检索请求与响应 Schema。
依赖: pydantic
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

# ============================================
# region 请求模型
# ============================================


class SearchRequest(BaseModel):
    """检索请求。"""

    query: str = Field(..., min_length=1)
    knowledge_base_id: int = Field(..., gt=0)
    top_k: int = Field(default=5, ge=1)


# endregion
# ============================================

# ============================================
# region 响应模型
# ============================================


class SearchResultItem(BaseModel):
    """检索结果项。"""

    chunk_text: str
    score: float
    document_id: int
    filename: str
    chunk_index: int


class SearchResponse(BaseModel):
    """检索响应。"""

    results: List[SearchResultItem]


# endregion
# ============================================
