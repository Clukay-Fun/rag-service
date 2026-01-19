"""
文件名: retriever.py
描述: 检索服务，包含向量检索、关键词检索与可选 rerank。
主要功能:
    - 向量相似度搜索（pgvector）
    - 关键词搜索（tsvector / ilike / trigram）
    - 文档合并与可选 rerank
依赖: httpx, sqlalchemy, app.config, app.services.embedding
"""

from typing import List, Dict, Any, Optional, Tuple

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    RERANK_MODEL,
    VECTOR_TOP_K,
    RERANK_TOP_K,
    SIMILARITY_THRESHOLD,
    RAG_SCHEMA,
    KEYWORD_SEARCH_ENABLED,
    KEYWORD_TOP_K,
    KEYWORD_TSVECTOR_COLLECTIONS,
    KEYWORD_ILIKE_COLLECTIONS,
    TRGM_SIMILARITY_THRESHOLD,
)
from app.services.embedding import get_embedding
from app.db.models import Document


# ============================================
# region 向量检索
# ============================================
def vector_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = VECTOR_TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[Tuple[Document, float]]:
    """
    使用 pgvector 进行向量相似度检索。

    参数:
        db: 数据库 Session
        query: 查询文本
        collection: 集合名称
        top_k: 返回数量
        threshold: 最大距离阈值
    返回:
        (Document, distance) 列表
    """
    if not query or not query.strip():
        return []
    top_k = max(1, min(top_k, 100))
    threshold = max(0.0, threshold)

    query_embedding = get_embedding(query)
    if not query_embedding:
        return []

    vector_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql = text(f"""
        SELECT
            id,
            embedding <-> :query_vec AS distance
        FROM {RAG_SCHEMA}.documents
        WHERE collection = :collection
          AND embedding IS NOT NULL
          AND embedding <-> :query_vec < :threshold
        ORDER BY distance
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query_vec": vector_str,
            "collection": collection,
            "threshold": threshold,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    documents_with_distance: List[Tuple[Document, float]] = []
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_distance.append((doc, row.distance))

    return documents_with_distance
# endregion
# ============================================


# ============================================
# region 关键词检索
# ============================================
def _tsvector_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int,
) -> List[Tuple[Document, float]]:
    sql = text(f"""
        SELECT
            id,
            ts_rank_cd(
                to_tsvector('simple', content),
                plainto_tsquery('simple', :query)
            ) AS rank
        FROM {RAG_SCHEMA}.documents
        WHERE collection = :collection
          AND to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
        ORDER BY rank DESC
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query": query,
            "collection": collection,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    documents_with_rank: List[Tuple[Document, float]] = []
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_rank.append((doc, float(row.rank)))

    return documents_with_rank


def _ilike_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int,
) -> List[Tuple[Document, float]]:
    sql = text(f"""
        SELECT
            id,
            similarity(
                lower(coalesce(doc_metadata->>'name', '')),
                lower(:query)
            ) AS rank
        FROM {RAG_SCHEMA}.documents
        WHERE collection = :collection
          AND (
              lower(coalesce(doc_metadata->>'name', ''))
                  ILIKE '%' || lower(:query) || '%'
              OR similarity(
                  lower(coalesce(doc_metadata->>'name', '')),
                  lower(:query)
              ) >= :min_similarity
          )
        ORDER BY rank DESC
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query": query,
            "collection": collection,
            "top_k": top_k,
            "min_similarity": TRGM_SIMILARITY_THRESHOLD,
        },
    )

    rows = result.fetchall()
    documents_with_rank: List[Tuple[Document, float]] = []
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_rank.append((doc, float(row.rank)))

    return documents_with_rank


def _content_ilike_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int,
) -> List[Tuple[Document, float]]:
    sql = text(f"""
        SELECT
            id,
            similarity(
                lower(content),
                lower(:query)
            ) AS rank
        FROM {RAG_SCHEMA}.documents
        WHERE collection = :collection
          AND lower(content) ILIKE '%' || lower(:query) || '%'
        ORDER BY rank DESC
        LIMIT :top_k
    """)

    result = db.execute(
        sql,
        {
            "query": query,
            "collection": collection,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()
    documents_with_rank: List[Tuple[Document, float]] = []
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_rank.append((doc, float(row.rank)))

    return documents_with_rank


def keyword_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = KEYWORD_TOP_K,
) -> List[Tuple[Document, float]]:
    """
    关键词检索，根据 collection 选择 tsvector 或 ilike 策略。
    """
    if not query or not query.strip():
        return []
    top_k = max(1, min(top_k, 100))

    if collection in KEYWORD_TSVECTOR_COLLECTIONS:
        res = _tsvector_search(db, query, collection, top_k)
        if res:
            return res
        # 中文未分词回退 content ilike
        return _content_ilike_search(db, query, collection, top_k)

    if collection in KEYWORD_ILIKE_COLLECTIONS:
        return _ilike_search(db, query, collection, top_k)

    return []
# endregion
# ============================================


# ============================================
# region Rerank
# ============================================
def rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = RERANK_TOP_K,
) -> List[Dict[str, Any]]:
    """使用外部模型对结果 rerank。"""
    if not documents:
        return []
    if not (SILICONFLOW_API_KEY and SILICONFLOW_BASE_URL and RERANK_MODEL):
        return documents[:top_k]

    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/rerank",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": RERANK_MODEL,
                "query": query,
                "documents": [doc["content"] for doc in documents],
                "top_n": top_k,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        reranked = []
        for item in result.get("results", []):
            idx = item["index"]
            score = item["relevance_score"]
            doc = documents[idx].copy()
            doc["rerank_score"] = score
            reranked.append(doc)
        return reranked or documents[:top_k]
    except httpx.HTTPError as exc:  # pragma: no cover
        print(f"[rerank] http error: {exc}")
    except Exception as exc:  # pragma: no cover
        print(f"[rerank] failed: {exc}")
    return documents[:top_k]
# endregion
# ============================================


# ============================================
# region 工具
# ============================================
def _distance_to_similarity(distance: float) -> float:
    return round(1 - distance / 2, 4)
# endregion
# ============================================


# ============================================
# region 检索主流程
# ============================================
def _merge_results(
    vector_results: List[Tuple[Document, float]],
    keyword_results: List[Tuple[Document, float]],
) -> List[Dict[str, Any]]:
    combined: Dict[int, Dict[str, Any]] = {}

    for doc, distance in vector_results:
        combined[doc.id] = {
            "doc": doc,
            "similarity": _distance_to_similarity(distance),
        }

    for doc, score in keyword_results:
        similarity = round(score, 4)
        if doc.id in combined:
            combined[doc.id]["similarity"] = max(
                combined[doc.id]["similarity"],
                similarity,
            )
        else:
            combined[doc.id] = {"doc": doc, "similarity": similarity}

    results: List[Dict[str, Any]] = []
    for item in combined.values():
        doc = item["doc"]
        results.append(
            {
                "id": doc.id,
                "source_id": doc.source_id,
                "content": doc.content,
                "metadata": doc.doc_metadata,
                "similarity": item["similarity"],
            }
        )

    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results


def hybrid_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = VECTOR_TOP_K,
    rerank_top_k: int = RERANK_TOP_K,
    use_rerank: bool = True,
) -> List[Dict[str, Any]]:
    """
    混合检索：向量检索 + 可选关键词检索 + 可选 rerank。
    """
    if not query or not collection:
        return []

    vector_results = vector_search(db, query, collection, top_k=top_k)
    keyword_results: List[Tuple[Document, float]] = []

    if KEYWORD_SEARCH_ENABLED:
        keyword_results = keyword_search(db, query, collection, top_k=KEYWORD_TOP_K)

    documents = _merge_results(vector_results, keyword_results)
    if not documents:
        return []

    if use_rerank and len(documents) > rerank_top_k and rerank_top_k > 0:
        documents = rerank(query, documents, top_k=rerank_top_k)
    else:
        documents = documents[:rerank_top_k]

    return documents
# endregion
# ============================================
