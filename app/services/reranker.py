"""
文件名: reranker.py
描述: 重排服务占位实现。
主要功能:
    - 将查询与候选文本进行重排打分。
依赖: httpx
"""

from __future__ import annotations

from typing import Callable, List

import httpx

from app.config import get_settings
from app.errors import AppError, ErrorDetail

# ============================================
# region 重排接口
# ============================================


def rerank_texts(query: str, candidates: List[str]) -> List[float]:
    """
    重排打分（远程调用）。

    参数:
        query: 查询文本。
        candidates: 候选文本列表。
    返回:
        分数列表（与候选数量一致）。
    """
    if not candidates:
        return []
    settings = get_settings()
    if not settings.rerank_model:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="重排模型未配置",
            details=[ErrorDetail(field="rerank_model", code="MISSING", message="缺少重排模型名称")],
        )
    if not settings.rerank_api_key:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="重排模型未配置",
            details=[ErrorDetail(field="rerank_api_key", code="MISSING", message="缺少重排模型密钥")],
        )
    if not settings.rerank_url and not settings.rerank_base_url:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="重排模型未配置",
            details=[ErrorDetail(field="rerank_base_url", code="MISSING", message="缺少重排模型地址")],
        )

    url = settings.rerank_url if settings.rerank_url else settings.rerank_base_url.rstrip("/") + "/rerank"
    headers = {"Authorization": f"Bearer {settings.rerank_api_key}"}
    payload = {"model": settings.rerank_model, "query": query, "documents": candidates}
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=settings.llm_timeout_seconds)
    except httpx.RequestError as exc:
        raise AppError(
            status_code=502,
            code="UPSTREAM_RERANK_ERROR",
            message="重排模型调用失败",
            details=[ErrorDetail(field="rerank", code="REQUEST_ERROR", message=str(exc))],
        ) from exc
    if response.status_code >= 400:
        raise AppError(
            status_code=502,
            code="UPSTREAM_RERANK_ERROR",
            message="重排模型调用失败",
            details=[ErrorDetail(field="rerank", code=str(response.status_code), message=response.text)],
        )

    payload_json = response.json()
    scores = _parse_rerank_response(payload_json, len(candidates))
    if len(scores) != len(candidates):
        raise AppError(
            status_code=502,
            code="UPSTREAM_RERANK_ERROR",
            message="重排模型返回数量不一致",
            details=[
                ErrorDetail(
                    field="rerank",
                    code="COUNT_MISMATCH",
                    message="重排分数数量与候选数量不一致",
                )
            ],
        )
    return scores


_DEFAULT_RERANKER = rerank_texts


def set_reranker(reranker: Callable[[str, List[str]], List[float]]) -> None:
    """
    设置全局 rerank 实现（用于测试或替换实现）。

    参数:
        reranker: rerank 函数。
    """
    global rerank_texts
    rerank_texts = reranker


def reset_reranker() -> None:
    """
    重置 rerank 实现为默认占位。
    """
    global rerank_texts
    rerank_texts = _DEFAULT_RERANKER


def is_reranker_ready() -> bool:
    """
    判断 rerank 实现是否就绪。

    返回:
        是否已配置 rerank 实现。
    """
    if rerank_texts is not _DEFAULT_RERANKER:
        return True
    settings = get_settings()
    return bool(
        (settings.rerank_url or settings.rerank_base_url)
        and settings.rerank_api_key
        and settings.rerank_model
    )


def _parse_rerank_response(payload: object, total: int) -> List[float]:
    """
    解析重排模型返回结果。

    参数:
        payload: 返回 JSON。
        total: 候选数量。
    返回:
        分数列表。
    """
    if not isinstance(payload, dict):
        return []
    if "results" in payload and isinstance(payload.get("results"), list):
        results = payload.get("results", [])
        scores = [0.0 for _ in range(total)]
        filled = 0
        for index, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            score = item.get("relevance_score", item.get("score"))
            idx = item.get("index")
            if idx is None:
                idx = index
            if isinstance(idx, int) and 0 <= idx < total and score is not None:
                scores[idx] = float(score)
                filled += 1
        if filled:
            return scores
    if "data" in payload and isinstance(payload.get("data"), list):
        data = payload.get("data", [])
        if data and isinstance(data[0], dict):
            scores = [float(item.get("score", item.get("relevance_score", 0.0))) for item in data]
            return scores
        if data and isinstance(data[0], (int, float)):
            return [float(value) for value in data]
    if "scores" in payload and isinstance(payload.get("scores"), list):
        return [float(value) for value in payload.get("scores", [])]
    return []


# endregion
# ============================================
