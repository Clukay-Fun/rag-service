"""
文件名: document.py
描述: 文档上传与状态查询服务。
主要功能:
    - 校验上传文件与知识库状态。
    - 创建文档记录并查询/删除文档。
依赖: SQLAlchemy, FastAPI
"""

from __future__ import annotations

import os
from typing import Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, DocumentStatus, KnowledgeBase, KnowledgeBaseStatus
from app.errors import AppError, ErrorDetail

# ============================================
# region 上传校验
# ============================================


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
}

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/markdown",
    "text/html",
    "image/png",
    "image/jpeg",
}


def _get_upload_size(upload_file: UploadFile) -> int:
    """
    获取上传文件大小。

    参数:
        upload_file: 上传文件对象。
    返回:
        文件大小（字节）。
    """
    if upload_file.file is None:
        return 0
    current = upload_file.file.tell()
    upload_file.file.seek(0, os.SEEK_END)
    size = upload_file.file.tell()
    upload_file.file.seek(current)
    return size


def _ensure_kb_available(db: Session, kb_id: int) -> KnowledgeBase:
    """
    校验知识库存在且可用。

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
            details=[ErrorDetail(field="knowledge_base_id", code="NOT_FOUND", message="知识库不存在")],
        )
    if kb.status in {KnowledgeBaseStatus.DISABLED, KnowledgeBaseStatus.DELETED}:
        raise AppError(
            status_code=403,
            code="KNOWLEDGE_BASE_UNAVAILABLE",
            message="知识库不可用",
            details=[ErrorDetail(field="knowledge_base_id", code="UNAVAILABLE", message="知识库不可用")],
        )
    return kb


def _validate_upload_file(upload_file: UploadFile, max_size: int) -> None:
    """
    校验上传文件的格式与大小。

    参数:
        upload_file: 上传文件对象。
        max_size: 允许的最大文件大小（字节）。
    """
    filename = upload_file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    content_type = upload_file.content_type or ""
    if ext not in SUPPORTED_EXTENSIONS and content_type not in SUPPORTED_CONTENT_TYPES:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise AppError(
            status_code=415,
            code="UNSUPPORTED_MEDIA_TYPE",
            message=f"不支持的文件格式，支持格式: {supported}",
            details=[ErrorDetail(field="file", code="UNSUPPORTED", message="文件格式不被支持")],
        )

    size = _get_upload_size(upload_file)
    if size > max_size:
        raise AppError(
            status_code=413,
            code="PAYLOAD_TOO_LARGE",
            message="上传文件超过大小限制",
            details=[ErrorDetail(field="file", code="TOO_LARGE", message="上传文件超过大小限制")],
        )


# endregion
# ============================================

# ============================================
# region 文档 CRUD
# ============================================


def create_document(
    db: Session,
    kb_id: int,
    upload_file: UploadFile,
    max_size: int,
) -> Document:
    """
    创建文档记录。

    参数:
        db: 数据库会话。
        kb_id: 知识库 ID。
        upload_file: 上传文件对象。
        max_size: 最大文件大小限制。
    返回:
        Document 对象。
    """
    _ensure_kb_available(db, kb_id)
    _validate_upload_file(upload_file, max_size)

    document = Document(
        knowledge_base_id=kb_id,
        filename=upload_file.filename or "unknown",
        status=DocumentStatus.PROCESSING,
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, document_id: int) -> Document:
    """
    获取文档详情。

    参数:
        db: 数据库会话。
        document_id: 文档 ID。
    返回:
        Document 对象。
    """
    document = db.get(Document, document_id)
    if document is None:
        raise AppError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="文档不存在",
        )
    return document


def list_documents(
    db: Session,
    kb_id: int,
    *,
    page: int,
    page_size: int,
    status: Optional[DocumentStatus] = None,
) -> Tuple[list[Document], int]:
    """
    分页查询文档列表。

    参数:
        db: 数据库会话。
        kb_id: 知识库 ID。
        page: 页码（从 1 开始）。
        page_size: 每页大小。
        status: 文档状态过滤。
    返回:
        (items, total) 元组。
    """
    _ = _ensure_kb_available(db, kb_id)
    filters = [Document.knowledge_base_id == kb_id]
    if status:
        filters.append(Document.status == status)

    total = db.execute(
        select(func.count()).select_from(Document).where(*filters)
    ).scalar_one()

    stmt = (
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()
    return items, total


def delete_document(db: Session, document_id: int) -> None:
    """
    删除文档并清理分块记录。

    参数:
        db: 数据库会话。
        document_id: 文档 ID。
    """
    document = db.get(Document, document_id)
    if document is None:
        raise AppError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="文档不存在",
        )
    if document.status == DocumentStatus.DELETED:
        raise AppError(
            status_code=410,
            code="DOCUMENT_DELETED",
            message="文档已删除",
        )

    document.status = DocumentStatus.DELETED
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    db.commit()


# endregion
# ============================================
