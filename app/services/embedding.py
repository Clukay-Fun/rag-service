"""
文件名: embedding.py
描述: 文档分块向量写入与事务控制服务。
主要功能:
    - 生成并归一化 embedding。
    - 事务性写入分块向量并更新文档状态。
依赖: SQLAlchemy
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, List

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, DocumentStatus
from app.errors import AppError
from app.services.chunker import Chunk

# ============================================
# region 向量处理
# ============================================


def l2_normalize(vector: Iterable[float]) -> List[float]:
    """
    对向量进行 L2 归一化。

    参数:
        vector: 输入向量。
    返回:
        归一化后的向量。
    """
    values = [float(v) for v in vector]
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return values
    return [v / norm for v in values]


# endregion
# ============================================

# ============================================
# region 写入与事务控制
# ============================================


def persist_embeddings(
    db: Session,
    *,
    document_id: int,
    chunks: List[Chunk],
    embed_fn: Callable[[List[str]], List[List[float]]],
    embedding_dim: int = 1024,
) -> Document:
    """
    生成并写入文档分块向量，保证事务一致性。

    参数:
        db: 数据库会话。
        document_id: 文档 ID。
        chunks: 分块列表。
        embed_fn: 向量化函数，输入文本列表输出向量列表。
        embedding_dim: 向量维度，默认 1024。
    返回:
        更新后的 Document 对象。
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

    texts = [chunk.text for chunk in chunks]
    try:
        embeddings = embed_fn(texts)
        if len(embeddings) != len(chunks):
            raise ValueError("embedding 数量与分块数量不一致")
        normalized = []
        for embedding in embeddings:
            if len(embedding) != embedding_dim:
                raise ValueError("embedding 向量维度不一致")
            normalized.append(l2_normalize(embedding))

        transaction = db.begin_nested() if db.in_transaction() else db.begin()
        with transaction:
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            for chunk, embedding in zip(chunks, normalized):
                db.add(
                    DocumentChunk(
                        knowledge_base_id=document.knowledge_base_id,
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        chunk_text=chunk.text,
                        metadata_json=chunk.metadata,
                        embedding=embedding,
                    )
                )
            document.chunk_count = len(chunks)
            document.status = DocumentStatus.COMPLETED
            document.error_message = None
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            db.commit()
        raise AppError(
            status_code=500,
            code="INTERNAL_ERROR",
            message="向量写入失败",
        ) from exc

    db.refresh(document)
    return document


# endregion
# ============================================
