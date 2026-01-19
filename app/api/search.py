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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
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
    collection: str = Field(..., min_length=1, description="集合名")
    top_k: int = Field(default=VECTOR_TOP_K, ge=1, le=50, description="返回数量")
    use_rerank: bool = Field(default=True, description="是否执行 rerank")


class IndexDocument(BaseModel):
    content: str = Field(..., min_length=1, description="文档内容")
    source_id: Optional[int] = Field(None, description="来源 ID")
    metadata: dict = Field(default_factory=dict, description="元数据")


class IndexRequest(BaseModel):
    collection: str = Field(..., min_length=1, description="集合名")
    documents: List[IndexDocument] = Field(..., description="文档列表")
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
@router.post("/", response_model=SearchResponse, status_code=status.HTTP_200_OK)
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


@router.post("/index", response_model=IndexResponse, status_code=status.HTTP_200_OK)
async def index_documents(request: IndexRequest, db: Session = Depends(get_db)):
    """批量索引文档。"""
    indexed = 0
    failed = 0

    texts = [doc.content for doc in request.documents]
    embeddings = get_embeddings_batch(texts)

    if len(embeddings) != len(request.documents):
        raise HTTPException(status_code=500, detail="embedding batch size mismatch")

    for doc, embedding in zip(request.documents, embeddings):
        try:
            new_doc = Document(
                collection=request.collection,
                source_id=doc.source_id,
                content=doc.content,
                doc_metadata=doc.metadata,
                embedding=embedding,
            )
            db.add(new_doc)
            indexed += 1
        except Exception:
            failed += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"db commit failed: {exc}") from exc

    return IndexResponse(
        collection=request.collection,
        indexed=indexed,
        failed=failed,
    )


@router.delete(
    "/{collection}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def delete_collection(collection: str, db: Session = Depends(get_db)):
    """删除指定集合的全部文档。"""
    if not collection:
        raise HTTPException(status_code=400, detail="collection is required")

    deleted = db.query(Document).filter(Document.collection == collection).delete()
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"db commit failed: {exc}") from exc
    return {"collection": collection, "deleted": deleted}


@router.get(
    "/collections",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
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
