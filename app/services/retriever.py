"""
文件名: retriever.py
描述: 语义检索与重排服务。
主要功能:
    - 根据查询向量执行 pgvector 检索。
    - 调用 rerank 模型进行精排。
依赖: SQLAlchemy
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, DocumentStatus, KnowledgeBase, KnowledgeBaseStatus
from app.errors import AppError, ErrorDetail

# ============================================
# region 数据结构
# ============================================


@dataclass(frozen=True)
class SearchResult:
    """检索结果。"""

    chunk_text: str
    score: float
    document_id: int
    filename: str
    chunk_index: int


# endregion
# ============================================

# ============================================
# region 评分工具
# ============================================


def _sigmoid(value: float) -> float:
    """
    Sigmoid 归一化。

    参数:
        value: 原始分数。
    返回:
        归一化分数。
    """
    return 1 / (1 + math.exp(-value))


# endregion
# ============================================

# ============================================
# region 检索逻辑
# ============================================


def search_chunks(
    db: Session,
    *,
    knowledge_base_id: int,
    query_text: str,
    query_embedding: List[float],
    top_k: int,
    max_rerank_candidates: int,
    rerank_fn: Callable[[str, List[str]], List[float]],
) -> List[SearchResult]:
    """
    执行语义检索与重排。

    参数:
        db: 数据库会话。
        knowledge_base_id: 知识库 ID。
        query_text: 原始查询文本。
        query_embedding: 查询向量。
        top_k: 返回条数。
        max_rerank_candidates: rerank 最大候选数。
        rerank_fn: rerank 函数（query + 候选文本 => 分数列表）。
    返回:
        SearchResult 列表。
    """
    kb = db.get(KnowledgeBase, knowledge_base_id)
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

    candidate_count = min(top_k * 3, max_rerank_candidates)
    if candidate_count <= 0:
        return []

    stmt = (
        select(
            DocumentChunk,
            Document,
        )
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        .where(Document.status == DocumentStatus.COMPLETED)
    )
    dialect_name = db.get_bind().dialect.name if db.get_bind() is not None else ""
    if dialect_name != "sqlite" and hasattr(DocumentChunk.embedding, "cosine_distance"):
        stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
    stmt = stmt.limit(candidate_count)
    rows = db.execute(stmt).all()
    if not rows:
        return []

    chunks = [row[0] for row in rows]
    documents = {row[0].document_id: row[1] for row in rows}
    texts = [chunk.chunk_text for chunk in chunks]

    scores = rerank_fn(query_text, texts)
    if len(scores) != len(texts):
        raise AppError(
            status_code=500,
            code="INTERNAL_ERROR",
            message="重排结果数量不一致",
        )
    normalized = [_sigmoid(score) for score in scores]

    ranked = list(zip(chunks, normalized))
    ranked.sort(key=lambda item: item[1], reverse=True)
    top = ranked[:top_k]

    results = []
    for chunk, score in top:
        doc = documents.get(chunk.document_id)
        results.append(
            SearchResult(
                chunk_text=chunk.chunk_text,
                score=score,
                document_id=chunk.document_id,
                filename=doc.filename if doc else "",
                chunk_index=chunk.chunk_index,
            )
        )
    return results


# endregion
# ============================================
