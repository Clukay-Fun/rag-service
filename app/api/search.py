"""
RAG 搜索 API
提供向量检索、文档索引等接口
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document
from app.services.embedding import get_embedding, get_embeddings_batch
from app.services.retriever import hybrid_search, vector_search
from app.config import VECTOR_TOP_K, RERANK_TOP_K


# ============================================
# region 路由定义
# ============================================

router = APIRouter(prefix="/search", tags=["搜索"])

# endregion
# ============================================


# ============================================
# region 请求/响应模型
# ============================================

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, description="查询文本")
    collection: str = Field(..., description="数据集名称")
    top_k: int = Field(default=VECTOR_TOP_K, ge=1, le=50, description="检索数量")
    use_rerank: bool = Field(default=True, description="是否使用 Rerank")


class SearchResult(BaseModel):
    """搜索结果"""
    id: int
    source_id: Optional[int]
    content: str
    metadata: dict
    similarity: float
    rerank_score: Optional[float] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    collection: str
    count: int
    results: List[SearchResult]


class IndexRequest(BaseModel):
    """索引请求"""
    collection: str = Field(..., description="数据集名称")
    documents: List[dict] = Field(..., description="文档列表")


class IndexResponse(BaseModel):
    """索引响应"""
    collection: str
    indexed: int
    failed: int

# endregion
# ============================================


# ============================================
# region API 接口
# ============================================

@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    """
    语义搜索接口
    支持向量检索 + Rerank
    """
    results = hybrid_search(
        db=db,
        query=request.query,
        collection=request.collection,
        top_k=request.top_k,
        rerank_top_k=RERANK_TOP_K,
        use_rerank=request.use_rerank,
    )
    
    return SearchResponse(
        query=request.query,
        collection=request.collection,
        count=len(results),
        results=[SearchResult(**r) for r in results],
    )


@router.post("/index", response_model=IndexResponse)
async def index_documents(request: IndexRequest, db: Session = Depends(get_db)):
    """
    文档索引接口
    批量添加文档并生成向量
    """
    indexed = 0
    failed = 0
    
    # 提取文本用于批量生成向量
    texts = [doc.get("content", "") for doc in request.documents]
    embeddings = get_embeddings_batch(texts)
    
    for doc, embedding in zip(request.documents, embeddings):
        try:
            new_doc = Document(
                collection=request.collection,
                source_id=doc.get("source_id"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata", {}),
                embedding=embedding,
            )
            db.add(new_doc)
            indexed += 1
        except Exception as e:
            print(f"❌ 索引失败: {e}")
            failed += 1
    
    db.commit()
    print(f"✅ 索引完成: {indexed} 成功, {failed} 失败")
    
    return IndexResponse(
        collection=request.collection,
        indexed=indexed,
        failed=failed,
    )


@router.delete("/{collection}")
async def delete_collection(collection: str, db: Session = Depends(get_db)):
    """
    删除数据集
    """
    deleted = db.query(Document).filter(
        Document.collection == collection
    ).delete()
    
    db.commit()
    
    return {"collection": collection, "deleted": deleted}


@router.get("/collections")
async def list_collections(db: Session = Depends(get_db)):
    """
    列出所有数据集
    """
    from sqlalchemy import func
    
    results = db.query(
        Document.collection,
        func.count(Document.id).label("count")
    ).group_by(Document.collection).all()
    
    return {
        "collections": [
            {"name": r.collection, "count": r.count}
            for r in results
        ]
    }

# endregion
# ============================================
