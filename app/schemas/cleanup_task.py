"""
文件名: cleanup_task.py
描述: 清理任务相关的请求与响应模型。
主要功能:
    - 定义清理任务查询与重试的 Schema。
依赖: pydantic
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import CleanupTaskStatus

# ============================================
# region 响应模型
# ============================================


class CleanupTaskProgress(BaseModel):
    """清理任务进度。"""

    processed: int = Field(default=0, ge=0)
    total: Optional[int] = Field(default=None, ge=0)
    percentage: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class CleanupTaskRead(BaseModel):
    """清理任务查询响应。"""

    id: int
    knowledge_base_id: int
    status: CleanupTaskStatus
    progress: Optional[CleanupTaskProgress]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# endregion
# ============================================
