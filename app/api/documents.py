"""
文件名: documents.py
描述: 文档上传与查询 API 路由。
主要功能:
    - 提供文档上传、详情查询、列表查询与删除接口。
依赖: FastAPI, SQLAlchemy
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DocumentStatus
from app.schemas.document import DocumentCreateResponse, DocumentListResponse, DocumentRead
from app.services.document import create_document, delete_document, get_document, list_documents

# ============================================
# region 路由定义
# ============================================


router = APIRouter(tags=["documents"])


@router.post(
    "/knowledge_bases/{kb_id}/documents",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_document(
    kb_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentCreateResponse:
    """
    上传文档并创建摄取记录。
    """
    settings = request.app.state.settings
    document = create_document(db, kb_id, file, settings.max_document_size)
    return DocumentCreateResponse(document_id=document.id, status=document.status)


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentRead:
    """
    获取文档详情。
    """
    document = get_document(db, document_id)
    return DocumentRead.model_validate(document)


@router.get("/knowledge_bases/{kb_id}/documents", response_model=DocumentListResponse)
def list_document_items(
    kb_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[DocumentStatus] = Query(default=None),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """
    查询知识库下的文档列表。
    """
    items, total = list_documents(
        db,
        kb_id,
        page=page,
        page_size=page_size,
        status=status,
    )
    return DocumentListResponse(
        items=[DocumentRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_item(
    document_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """
    删除文档及关联分块。
    """
    delete_document(db, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# endregion
# ============================================
