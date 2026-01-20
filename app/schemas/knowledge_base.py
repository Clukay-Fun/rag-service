"""
文件名: knowledge_base.py
描述: 知识库相关的请求与响应模型。
主要功能:
    - 定义知识库创建、更新、查询与删除的 Schema。
依赖: pydantic
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.db.models import KnowledgeBaseStatus

# ============================================
# region 请求模型
# ============================================


class KnowledgeBaseCreate(BaseModel):
    """知识库创建请求。"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class KnowledgeBaseUpdate(BaseModel):
    """知识库更新请求。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[KnowledgeBaseStatus] = None


# endregion
# ============================================

# ============================================
# region 响应模型
# ============================================


class KnowledgeBaseRead(BaseModel):
    """知识库详情响应。"""

    id: int
    name: str
    description: Optional[str]
    status: KnowledgeBaseStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应。"""

    items: List[KnowledgeBaseRead]
    total: int
    page: int
    page_size: int


class KnowledgeBaseDeleteResponse(BaseModel):
    """知识库删除响应。"""

    cleanup_task_id: int


# endregion
# ============================================
