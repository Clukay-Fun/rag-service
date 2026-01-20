"""
文件名: knowledge_bases.py
描述: 知识库管理 API 路由。
主要功能:
    - 提供知识库创建、更新、删除与查询接口。
依赖: FastAPI, SQLAlchemy
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import KnowledgeBaseStatus
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseDeleteResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services.knowledge_base import (
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base,
    list_knowledge_bases,
    update_knowledge_base,
)

# ============================================
# region 路由定义
# ============================================


router = APIRouter(prefix="/knowledge_bases", tags=["knowledge_bases"])


@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_kb(payload: KnowledgeBaseCreate, db: Session = Depends(get_db)) -> KnowledgeBaseRead:
    """
    创建知识库。
    """
    kb = create_knowledge_base(db, payload)
    return KnowledgeBaseRead.model_validate(kb)


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
def get_kb(kb_id: int, db: Session = Depends(get_db)) -> KnowledgeBaseRead:
    """
    获取知识库详情。
    """
    kb = get_knowledge_base(db, kb_id)
    return KnowledgeBaseRead.model_validate(kb)


@router.get("", response_model=KnowledgeBaseListResponse)
def list_kb(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name_contains: Optional[str] = Query(default=None),
    status: Optional[KnowledgeBaseStatus] = Query(default=None),
    db: Session = Depends(get_db),
) -> KnowledgeBaseListResponse:
    """
    分页获取知识库列表。
    """
    items, total = list_knowledge_bases(
        db,
        page=page,
        page_size=page_size,
        name_contains=name_contains,
        status=status,
    )
    return KnowledgeBaseListResponse(
        items=[KnowledgeBaseRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
def update_kb(
    kb_id: int,
    payload: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    """
    更新知识库信息。
    """
    kb = update_knowledge_base(db, kb_id, payload)
    return KnowledgeBaseRead.model_validate(kb)


@router.delete("/{kb_id}", response_model=KnowledgeBaseDeleteResponse, status_code=202)
def delete_kb(kb_id: int, db: Session = Depends(get_db)) -> KnowledgeBaseDeleteResponse:
    """
    删除知识库并创建清理任务。
    """
    task = delete_knowledge_base(db, kb_id)
    return KnowledgeBaseDeleteResponse(cleanup_task_id=task.id)


# endregion
# ============================================
