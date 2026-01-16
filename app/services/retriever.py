"""
RAG 检索服务
实现向量检索、Rerank 和混合搜索
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
    向量相似度检索
    
    参数:
        db: 数据库会话
        query: 查询文本
        collection: 数据集名称
        top_k: 返回数量
        threshold: 相似度阈值
    
    返回:
        (Document, distance) 元组列表
    """
    # 生成查询向量
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("❌ 无法生成查询向量")
        return []
    
    # pgvector 余弦距离查询
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
    
    # 获取完整文档对象
    rows = result.fetchall()
    documents_with_distance = []
    
    for row in rows:
        doc = db.query(Document).filter(Document.id == row.id).first()
        if doc:
            documents_with_distance.append((doc, row.distance))
    
    print(f"🔍 向量检索: collection={collection}, 结果数={len(documents_with_distance)}")
    return documents_with_distance

# endregion
# ============================================


# ============================================
# region Rerank 重排序
# ============================================

def rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = RERANK_TOP_K,
) -> List[Dict[str, Any]]:
    """
    使用 Rerank 模型对检索结果重排序
    
    参数:
        query: 查询文本
        documents: 文档列表，每个包含 content 字段
        top_k: 保留数量
    
    返回:
        重排序后的文档列表（带 rerank_score）
    """
    if not documents:
        return []
    
    try:
        response = httpx.post(
            f"{SILICONFLOW_BASE_URL}/rerank",
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": RERANK_MODEL,
                "query": query,
                "documents": [doc["content"] for doc in documents],
                "top_n": top_k,
            },
            timeout=30.0
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
            
            print(f"🔄 Rerank 完成: {len(documents)} -> {len(reranked)}")
            return reranked
        else:
            print(f"❌ Rerank API 错误: {response.status_code}")
            return documents[:top_k]
            
    except Exception as e:
        print(f"❌ Rerank 失败: {e}")
        return documents[:top_k]

# endregion
# ============================================


# ============================================
# region 混合检索
# ============================================

def hybrid_search(
    db: Session,
    query: str,
    collection: str,
    top_k: int = VECTOR_TOP_K,
    rerank_top_k: int = RERANK_TOP_K,
    use_rerank: bool = True,
) -> List[Dict[str, Any]]:
    """
    混合检索：向量检索 + Rerank
    
    参数:
        db: 数据库会话
        query: 查询文本
        collection: 数据集名称
        top_k: 向量检索数量
        rerank_top_k: Rerank 后保留数量
        use_rerank: 是否使用 Rerank
    
    返回:
        检索结果列表
    """
    # 1. 向量检索
    vector_results = vector_search(db, query, collection, top_k=top_k)
    
    if not vector_results:
        return []
    
    # 2. 转换为字典格式
    documents = []
    for doc, distance in vector_results:
        documents.append({
            "id": doc.id,
            "source_id": doc.source_id,
            "content": doc.content,
            "metadata": doc.metadata,
            "similarity": round(1 - distance / 2, 4),  # 距离转相似度
        })
    
    # 3. Rerank（可选）
    if use_rerank and len(documents) > rerank_top_k:
        documents = rerank(query, documents, top_k=rerank_top_k)
    else:
        documents = documents[:rerank_top_k]
    
    return documents

# endregion
# ============================================
