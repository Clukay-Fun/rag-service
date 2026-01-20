"""
文件名: search.py
描述: 语义检索与重排 API。
主要功能:
    - 接收查询请求并返回检索结果。
依赖: FastAPI, SQLAlchemy
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services import embedding as embedding_service
from app.services import reranker as reranker_service
from app.services.embedding import l2_normalize
from app.services.retriever import search_chunks

# ============================================
# region 路由定义
# ============================================


router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_documents(
    payload: SearchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    执行语义检索与重排。
    """
    settings = request.app.state.settings
    top_k = min(payload.top_k, settings.max_top_k)
    embeddings = embedding_service.embed_texts([payload.query])
    query_embedding = l2_normalize(embeddings[0])

    results = search_chunks(
        db,
        knowledge_base_id=payload.knowledge_base_id,
        query_text=payload.query,
        query_embedding=query_embedding,
        top_k=top_k,
        max_rerank_candidates=settings.max_rerank_candidates,
        rerank_fn=reranker_service.rerank_texts,
    )
    return SearchResponse(
        results=[
            SearchResultItem(
                chunk_text=item.chunk_text,
                score=item.score,
                document_id=item.document_id,
                filename=item.filename,
                chunk_index=item.chunk_index,
            )
            for item in results
        ]
    )


# endregion
# ============================================
