"""
文件名: search.py
描述: 搜索与索引相关的 HTTP API。
主要功能:
    - 语义搜索（可选 rerank）
    - 文档批量入库
    - 集合管理（删除、列表）
依赖: fastapi, pydantic, sqlalchemy, app.services.retriever
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Document
from app.services.embedding import get_embeddings_batch
from app.services.retriever import hybrid_search
from app.config import VECTOR_TOP_K, RERANK_TOP_K

router = APIRouter(prefix="/search", tags=["search"])


# ============================================
# region 请求模型
# ============================================
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="查询文本")
    collection: str = Field(..., description="集合名")
    top_k: int = Field(default=VECTOR_TOP_K, ge=1, le=50, description="返回数量")
    use_rerank: bool = Field(default=True, description="是否执行 rerank")


class IndexRequest(BaseModel):
    collection: str = Field(..., description="集合名")
    documents: List[dict] = Field(..., description="文档列表")
# endregion
# ============================================


# ============================================
# region 响应模型
# ============================================
class SearchResult(BaseModel):
    id: int
    source_id: Optional[int]
    content: str
    metadata: dict
    similarity: float
    rerank_score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    collection: str
    count: int
    results: List[SearchResult]


class IndexResponse(BaseModel):
    collection: str
    indexed: int
    failed: int
# endregion
# ============================================


# ============================================
# region API
# ============================================
@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    """语义搜索接口。"""
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
    """批量索引文档。"""
    indexed = 0
    failed = 0

    texts = [doc.get("content") or doc.get("text") or "" for doc in request.documents]
    embeddings = get_embeddings_batch(texts)

    if len(embeddings) != len(request.documents):
        raise HTTPException(status_code=500, detail="embedding batch size mismatch")

    for doc, embedding in zip(request.documents, embeddings):
        try:
            content = doc.get("content") or doc.get("text") or ""
            new_doc = Document(
                collection=request.collection,
                source_id=doc.get("source_id"),
                content=content,
                doc_metadata=doc.get("metadata", {}),
                embedding=embedding,
            )
            db.add(new_doc)
            indexed += 1
        except Exception:
            failed += 1

    db.commit()

    return IndexResponse(
        collection=request.collection,
        indexed=indexed,
        failed=failed,
    )


@router.delete("/{collection}")
async def delete_collection(collection: str, db: Session = Depends(get_db)):
    """删除指定集合的全部文档。"""
    deleted = db.query(Document).filter(Document.collection == collection).delete()
    db.commit()
    return {"collection": collection, "deleted": deleted}


@router.get("/collections")
async def list_collections(db: Session = Depends(get_db)):
    """列出当前所有集合及计数。"""
    from sqlalchemy import func

    results = (
        db.query(
            Document.collection,
            func.count(Document.id).label("count"),
        )
        .group_by(Document.collection)
        .all()
    )

    return {
        "collections": [
            {"name": r.collection, "count": r.count}
            for r in results
        ]
    }
# endregion
# ============================================
