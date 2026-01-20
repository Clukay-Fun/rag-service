"""
文件名: observability.py
描述: 健康探针与可观测性 API。
主要功能:
    - 提供 /health、/ready、/metrics 接口。
依赖: FastAPI, SQLAlchemy
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DocumentChunk, KnowledgeBase, KnowledgeBaseStatus
from app.services import embedding as embedding_service
from app.services import reranker as reranker_service
from app.services.metrics import PROMETHEUS_CONTENT_TYPE, format_metrics, set_active_knowledge_bases, set_chunks_total

# ============================================
# region 路由定义
# ============================================


router = APIRouter(tags=["observability"])


@router.get("/health")
def health_check() -> dict:
    """
    存活探针，仅验证进程存活。
    """
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    就绪探针，检查数据库与模型是否可用。
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        request.app.state.logger.exception(
            "就绪检查数据库失败",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
        raise HTTPException(status_code=503, detail="服务未就绪") from exc

    if not embedding_service.is_embedder_ready() or not reranker_service.is_reranker_ready():
        raise HTTPException(status_code=503, detail="服务未就绪")

    return {"status": "ready"}


@router.get("/metrics")
def metrics(request: Request, db: Session = Depends(get_db)) -> Response:
    """
    输出 Prometheus 文本格式指标。
    """
    try:
        active_count = db.execute(
            select(func.count()).select_from(KnowledgeBase).where(KnowledgeBase.status == KnowledgeBaseStatus.ENABLED)
        ).scalar_one()
        chunk_count = db.execute(select(func.count()).select_from(DocumentChunk)).scalar_one()
        set_active_knowledge_bases(int(active_count))
        set_chunks_total(int(chunk_count))
    except Exception:
        request.app.state.logger.exception(
            "指标查询失败",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
    return Response(content=format_metrics(), media_type=PROMETHEUS_CONTENT_TYPE)


# endregion
# ============================================
