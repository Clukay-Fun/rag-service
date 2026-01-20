"""
文件名: document.py
描述: 文档相关的请求与响应模型。
主要功能:
    - 定义文档上传、查询与删除的 Schema。
依赖: pydantic
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.db.models import DocumentStatus

# ============================================
# region 响应模型
# ============================================


class DocumentCreateResponse(BaseModel):
    """文档上传响应。"""

    document_id: int
    status: DocumentStatus


class DocumentRead(BaseModel):
    """文档详情响应。"""

    id: int
    knowledge_base_id: int
    filename: str
    status: DocumentStatus
    error_message: Optional[str]
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """文档列表响应。"""

    items: List[DocumentRead]
    total: int
    page: int
    page_size: int


# endregion
# ============================================
