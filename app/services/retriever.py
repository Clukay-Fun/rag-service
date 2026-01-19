"""
RAG retrieval service: vector search, keyword search, and rerank.
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
# region 检索
# ============================================
def vector_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = VECTOR_TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[Tuple[Document, float]]:
    """Vector similarity search using pgvector."""
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

    result = db.execute(sql, {
        "query_vec": vector_str,
        "collection": collection,
        "threshold": threshold,
        "top_k": top_k,
    })

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
# region 检索
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

    result = db.execute(sql, {
        "query": query,
        "collection": collection,
        "top_k": top_k,
    })

    rows = result.fetchall()
    documents_with_rank: List[Tuple[Document, float]] = []
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_rank.append((doc, float(row.rank)))

    return documents_with_rank
# endregion
# ============================================


# ============================================
# region 检索
# ============================================
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

    result = db.execute(sql, {
        "query": query,
        "collection": collection,
        "top_k": top_k,
        "min_similarity": TRGM_SIMILARITY_THRESHOLD,
    })

    rows = result.fetchall()
    documents_with_rank: List[Tuple[Document, float]] = []
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_rank.append((doc, float(row.rank)))

    return documents_with_rank
# endregion
# ============================================


# ============================================
# region 检索
# ============================================
def keyword_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = KEYWORD_TOP_K,
) -> List[Tuple[Document, float]]:
    """Keyword search based on collection strategy."""
    if not query or not query.strip():
        return []

    if collection in KEYWORD_TSVECTOR_COLLECTIONS:
        return _tsvector_search(db, query, collection, top_k)

    if collection in KEYWORD_ILIKE_COLLECTIONS:
        return _ilike_search(db, query, collection, top_k)

    return []
# endregion
# ============================================


# ============================================
# region 重排序
# ============================================
def rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = RERANK_TOP_K,
) -> List[Dict[str, Any]]:
    """Rerank documents using external model."""
    if not documents:
        return []

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

        if response.status_code == 200:
            result = response.json()
            reranked = []

            for item in result.get("results", []):
                idx = item["index"]
                score = item["relevance_score"]
                doc = documents[idx].copy()
                doc["rerank_score"] = score
                reranked.append(doc)

            return reranked
        return documents[:top_k]

    except Exception:
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
# region 检索
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
        results.append({
            "id": doc.id,
            "source_id": doc.source_id,
            "content": doc.content,
            "metadata": doc.doc_metadata,
            "similarity": item["similarity"],
        })

    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results
# endregion
# ============================================


# ============================================
# region 检索
# ============================================
def hybrid_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = VECTOR_TOP_K,
    rerank_top_k: int = RERANK_TOP_K,
    use_rerank: bool = True,
) -> List[Dict[str, Any]]:
    """Hybrid search: vector + keyword (optional), with rerank."""
    vector_results = vector_search(db, query, collection, top_k=top_k)
    keyword_results: List[Tuple[Document, float]] = []

    if KEYWORD_SEARCH_ENABLED:
        keyword_results = keyword_search(db, query, collection, top_k=KEYWORD_TOP_K)

    documents = _merge_results(vector_results, keyword_results)
    if not documents:
        return []

    if use_rerank and len(documents) > rerank_top_k:
        documents = rerank(query, documents, top_k=rerank_top_k)
    else:
        documents = documents[:rerank_top_k]

    return documents
# endregion
# ============================================
