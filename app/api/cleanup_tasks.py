"""
文件名: cleanup_tasks.py
描述: 清理任务 API 路由。
主要功能:
    - 查询清理任务状态。
    - 失败任务重试。
依赖: FastAPI, SQLAlchemy
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.cleanup_task import CleanupTaskRead
from app.services.cleanup_task import get_cleanup_task, retry_cleanup_task

# ============================================
# region 路由定义
# ============================================


router = APIRouter(prefix="/cleanup_tasks", tags=["cleanup_tasks"])


@router.get("/{task_id}", response_model=CleanupTaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)) -> CleanupTaskRead:
    """
    查询清理任务状态。
    """
    task = get_cleanup_task(db, task_id)
    return CleanupTaskRead.model_validate(task)


@router.post("/{task_id}/retry", response_model=CleanupTaskRead, status_code=status.HTTP_202_ACCEPTED)
def retry_task(task_id: int, db: Session = Depends(get_db)) -> CleanupTaskRead:
    """
    重试失败的清理任务。
    """
    task = retry_cleanup_task(db, task_id)
    return CleanupTaskRead.model_validate(task)


# endregion
# ============================================
