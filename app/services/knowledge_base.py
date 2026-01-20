"""
文件名: knowledge_base.py
描述: 知识库业务服务。
主要功能:
    - 处理知识库的创建、更新、删除与查询逻辑。
依赖: SQLAlchemy
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import CleanupTask, CleanupTaskStatus, KnowledgeBase, KnowledgeBaseStatus
from app.errors import AppError
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate

# ============================================
# region 业务函数
# ============================================


def create_knowledge_base(db: Session, payload: KnowledgeBaseCreate) -> KnowledgeBase:
    """
    创建知识库。

    参数:
        db: 数据库会话。
        payload: 创建请求数据。
    返回:
        KnowledgeBase 对象。
    """
    exists = db.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == payload.name)
    ).scalar_one_or_none()
    if exists:
        raise AppError(
            status_code=409,
            code="KNOWLEDGE_BASE_NAME_CONFLICT",
            message="知识库名称已存在",
        )

    kb = KnowledgeBase(name=payload.name, description=payload.description)
    db.add(kb)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            status_code=409,
            code="KNOWLEDGE_BASE_NAME_CONFLICT",
            message="知识库名称已存在",
        )
    db.refresh(kb)
    return kb


def get_knowledge_base(db: Session, kb_id: int) -> KnowledgeBase:
    """
    获取知识库详情。

    参数:
        db: 数据库会话。
        kb_id: 知识库 ID。
    返回:
        KnowledgeBase 对象。
    """
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code="KNOWLEDGE_BASE_NOT_FOUND",
            message="知识库不存在",
        )
    return kb


def list_knowledge_bases(
    db: Session,
    *,
    page: int,
    page_size: int,
    name_contains: Optional[str] = None,
    status: Optional[KnowledgeBaseStatus] = None,
) -> Tuple[list[KnowledgeBase], int]:
    """
    分页查询知识库列表。

    参数:
        db: 数据库会话。
        page: 页码（从 1 开始）。
        page_size: 每页大小。
        name_contains: 名称模糊匹配。
        status: 状态过滤。
    返回:
        (items, total) 元组。
    """
    filters = []
    if name_contains:
        filters.append(KnowledgeBase.name.ilike(f"%{name_contains}%"))
    if status:
        filters.append(KnowledgeBase.status == status)

    total = db.execute(
        select(func.count()).select_from(KnowledgeBase).where(*filters)
    ).scalar_one()

    stmt = (
        select(KnowledgeBase)
        .where(*filters)
        .order_by(KnowledgeBase.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()
    return items, total


def update_knowledge_base(
    db: Session,
    kb_id: int,
    payload: KnowledgeBaseUpdate,
) -> KnowledgeBase:
    """
    更新知识库。

    参数:
        db: 数据库会话。
        kb_id: 知识库 ID。
        payload: 更新数据。
    返回:
        KnowledgeBase 对象。
    """
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code="KNOWLEDGE_BASE_NOT_FOUND",
            message="知识库不存在",
        )
    if kb.status == KnowledgeBaseStatus.DELETED:
        raise AppError(
            status_code=409,
            code="KNOWLEDGE_BASE_DELETED",
            message="知识库已删除，无法修改",
        )

    if payload.name and payload.name != kb.name:
        name_conflict = db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.name == payload.name)
            .where(KnowledgeBase.id != kb_id)
        ).scalar_one_or_none()
        if name_conflict:
            raise AppError(
                status_code=409,
                code="KNOWLEDGE_BASE_NAME_CONFLICT",
                message="知识库名称已存在",
            )
        kb.name = payload.name

    if payload.description is not None:
        kb.description = payload.description

    if payload.status is not None:
        if payload.status == KnowledgeBaseStatus.DELETED:
            raise AppError(
                status_code=409,
                code="KNOWLEDGE_BASE_DELETED",
                message="请使用删除接口删除知识库",
            )
        kb.status = payload.status

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            status_code=409,
            code="KNOWLEDGE_BASE_NAME_CONFLICT",
            message="知识库名称已存在",
        )
    db.refresh(kb)
    return kb


def delete_knowledge_base(db: Session, kb_id: int) -> CleanupTask:
    """
    删除知识库并创建清理任务。

    参数:
        db: 数据库会话。
        kb_id: 知识库 ID。
    返回:
        CleanupTask 对象。
    """
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        raise AppError(
            status_code=404,
            code="KNOWLEDGE_BASE_NOT_FOUND",
            message="知识库不存在",
        )
    if kb.status == KnowledgeBaseStatus.DELETED:
        raise AppError(
            status_code=409,
            code="KNOWLEDGE_BASE_DELETED",
            message="知识库已删除",
        )

    kb.status = KnowledgeBaseStatus.DELETED
    task = CleanupTask(
        knowledge_base_id=kb.id,
        status=CleanupTaskStatus.PENDING,
        progress={"processed": 0, "total": None, "percentage": None},
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# endregion
# ============================================
