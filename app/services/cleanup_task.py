"""
文件名: cleanup_task.py
描述: 清理任务业务逻辑。
主要功能:
    - 查询清理任务状态。
    - 执行清理任务并更新进度。
    - 失败任务重试。
依赖: SQLAlchemy
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import CleanupTask, CleanupTaskStatus, Document, DocumentChunk
from app.errors import AppError

# ============================================
# region 查询与重试
# ============================================


def get_cleanup_task(db: Session, task_id: int) -> CleanupTask:
    """
    获取清理任务详情。

    参数:
        db: 数据库会话。
        task_id: 清理任务 ID。
    返回:
        CleanupTask 对象。
    """
    task = db.get(CleanupTask, task_id)
    if task is None:
        raise AppError(
            status_code=404,
            code="CLEANUP_TASK_NOT_FOUND",
            message="清理任务不存在",
        )
    return task


def retry_cleanup_task(db: Session, task_id: int) -> CleanupTask:
    """
    重试清理任务（仅失败任务允许重试）。

    参数:
        db: 数据库会话。
        task_id: 清理任务 ID。
    返回:
        CleanupTask 对象。
    """
    task = get_cleanup_task(db, task_id)
    if task.status != CleanupTaskStatus.FAILED:
        raise AppError(
            status_code=409,
            code="CLEANUP_TASK_NOT_RETRYABLE",
            message="清理任务当前状态不可重试",
        )
    task.status = CleanupTaskStatus.PENDING
    task.error_message = None
    task.progress = {"processed": 0, "total": None, "percentage": None}
    db.commit()
    db.refresh(task)
    return task


# endregion
# ============================================

# ============================================
# region 执行器
# ============================================


def run_cleanup_task(db: Session, task_id: int) -> CleanupTask:
    """
    执行清理任务，删除该知识库关联文档与分块。

    参数:
        db: 数据库会话。
        task_id: 清理任务 ID。
    返回:
        CleanupTask 对象。
    """
    task = get_cleanup_task(db, task_id)
    if task.status == CleanupTaskStatus.COMPLETED:
        return task
    if task.status not in {CleanupTaskStatus.PENDING, CleanupTaskStatus.FAILED}:
        raise AppError(
            status_code=409,
            code="CLEANUP_TASK_NOT_RETRYABLE",
            message="清理任务当前状态不可执行",
        )

    task.status = CleanupTaskStatus.RUNNING
    task.error_message = None

    chunk_count = db.execute(
        select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.knowledge_base_id == task.knowledge_base_id
        )
    ).scalar_one()
    doc_count = db.execute(
        select(func.count()).select_from(Document).where(
            Document.knowledge_base_id == task.knowledge_base_id
        )
    ).scalar_one()

    total = int(chunk_count) + int(doc_count)
    task.progress = {"processed": 0, "total": total, "percentage": 0.0 if total else None}

    try:
        db.commit()
        db.execute(
            delete(DocumentChunk).where(DocumentChunk.knowledge_base_id == task.knowledge_base_id)
        )
        task.progress = {"processed": int(chunk_count), "total": total, "percentage": None}

        db.execute(
            delete(Document).where(Document.knowledge_base_id == task.knowledge_base_id)
        )
        task.status = CleanupTaskStatus.COMPLETED
        task.progress = {
            "processed": total,
            "total": total,
            "percentage": 1.0 if total else 1.0,
        }
        db.commit()
    except Exception as exc:
        db.rollback()
        task.status = CleanupTaskStatus.FAILED
        task.error_message = str(exc)
        db.commit()
    db.refresh(task)
    return task


# endregion
# ============================================
