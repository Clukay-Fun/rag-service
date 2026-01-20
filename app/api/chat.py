"""
文件名: chat.py
描述: 流式对话 API（SSE）。
主要功能:
    - 提供检索增强的流式对话接口。
依赖: FastAPI, SQLAlchemy
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Dict, List

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.database import get_db
from app.schemas.chat import ChatStreamRequest
from app.services import embedding as embedding_service
from app.services import reranker as reranker_service
from app.services.embedding import l2_normalize
from app.errors import AppError, ErrorDetail
from app.services.llm_client import stream_chat_completion
from app.services.retriever import search_chunks

# ============================================
# region 路由定义
# ============================================


router = APIRouter(prefix="/chat", tags=["chat"])


def _format_sse_event(event: str, payload: Dict[str, object]) -> str:
    """
    格式化 SSE 事件。

    参数:
        event: 事件名称。
        payload: 事件数据。
    返回:
        SSE 文本块。
    """
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\n" f"data: {data}\n\n"


def _build_messages(payload: ChatStreamRequest, sources: List[Dict[str, object]]) -> List[Dict[str, str]]:
    """
    构造对话消息列表。

    参数:
        payload: 请求数据。
        sources: 检索结果列表。
    返回:
        消息列表。
    """
    system_content = (
        "你是企业知识库助手，请根据给定资料回答用户问题。"
        "如果资料不足，请说明无法确定。"
    )
    source_lines = []
    for index, item in enumerate(sources, start=1):
        source_lines.append(f"[{index}] {item['filename']} (chunk {item['chunk_index']}) {item['chunk_text']}")
    context = "\n".join(source_lines) if source_lines else "未检索到相关资料。"

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
    if payload.history:
        for message in payload.history:
            messages.append({"role": message.role, "content": message.content})
    messages.append(
        {
            "role": "user",
            "content": f"问题: {payload.query}\n\n资料:\n{context}",
        }
    )
    return messages


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    检索增强的流式对话接口（SSE）。
    """
    settings: Settings = request.app.state.settings
    if not embedding_service.is_embedder_ready():
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="向量模型未就绪",
            details=[ErrorDetail(field="embedder", code="NOT_READY", message="向量模型未就绪")],
        )
    if not reranker_service.is_reranker_ready():
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="重排模型未就绪",
            details=[ErrorDetail(field="reranker", code="NOT_READY", message="重排模型未就绪")],
        )
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

    sources = [
        {
            "chunk_text": item.chunk_text,
            "score": item.score,
            "document_id": item.document_id,
            "filename": item.filename,
            "chunk_index": item.chunk_index,
        }
        for item in results
    ]
    messages = _build_messages(payload, sources)

    async def event_generator() -> AsyncIterator[str]:
        yield _format_sse_event("sources", {"results": sources})
        async for delta in stream_chat_completion(messages, settings=settings):
            yield _format_sse_event("delta", {"content": delta})
        yield _format_sse_event("done", {"finished": True})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# endregion
# ============================================
