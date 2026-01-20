"""
文件名: llm_client.py
描述: 模型 API 流式调用客户端。
主要功能:
    - 调用上游 LLM 流式接口并解析输出。
    - 提供可注入 streamer 以便测试。
依赖: httpx
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Callable, Dict, List

import httpx

from app.config import Settings
from app.errors import AppError, ErrorDetail

# ============================================
# region 类型定义
# ============================================


Streamer = Callable[[List[Dict[str, str]], Settings, float, int], AsyncIterator[str]]


# endregion
# ============================================

# ============================================
# region 默认实现
# ============================================


def _require_llm_settings(settings: Settings) -> None:
    """
    校验 LLM 配置是否完整。

    参数:
        settings: 配置对象。
    """
    if not settings.llm_base_url:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="模型服务未配置",
            details=[ErrorDetail(field="llm_base_url", code="MISSING", message="缺少模型服务地址")],
        )
    if not settings.llm_api_key:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="模型服务未配置",
            details=[ErrorDetail(field="llm_api_key", code="MISSING", message="缺少模型服务密钥")],
        )
    if not settings.llm_chat_model:
        raise AppError(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="模型服务未配置",
            details=[ErrorDetail(field="llm_chat_model", code="MISSING", message="缺少聊天模型名称")],
        )


def _build_chat_url(settings: Settings) -> str:
    """
    构建聊天接口地址。

    参数:
        settings: 配置对象。
    返回:
        完整的聊天接口 URL。
    """
    return settings.llm_base_url.rstrip("/") + "/chat/completions"


async def _default_streamer(
    messages: List[Dict[str, str]],
    settings: Settings,
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    """
    默认流式调用（OpenAI 兼容格式）。

    参数:
        messages: 消息列表。
        settings: 配置对象。
        temperature: 采样温度。
        max_tokens: 最大输出长度。
    返回:
        文本增量流。
    """
    _require_llm_settings(settings)
    url = _build_chat_url(settings)
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    payload = {
        "model": settings.llm_chat_model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    timeout = httpx.Timeout(settings.llm_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code >= 400:
                detail = await response.aread()
                raise AppError(
                    status_code=502,
                    code="UPSTREAM_LLM_ERROR",
                    message="模型服务调用失败",
                    details=[
                        ErrorDetail(
                            field="llm",
                            code=str(response.status_code),
                            message=detail.decode("utf-8", errors="ignore"),
                        )
                    ],
                )
            async for line in response.aiter_lines():
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                else:
                    continue
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                    delta = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                except (ValueError, TypeError, KeyError):
                    continue
                if delta:
                    yield delta


_STREAMER: Streamer = _default_streamer


# endregion
# ============================================

# ============================================
# region 公开接口
# ============================================


def set_streamer(streamer: Streamer) -> None:
    """
    设置自定义流式调用实现（用于测试或替换）。

    参数:
        streamer: 流式调用函数。
    """
    global _STREAMER
    _STREAMER = streamer


def reset_streamer() -> None:
    """
    重置为默认流式调用实现。
    """
    global _STREAMER
    _STREAMER = _default_streamer


async def stream_chat_completion(
    messages: List[Dict[str, str]],
    *,
    settings: Settings,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> AsyncIterator[str]:
    """
    生成流式对话增量内容。

    参数:
        messages: 消息列表。
        settings: 配置对象。
        temperature: 采样温度（可选，默认使用配置值）。
        max_tokens: 最大输出长度（可选，默认使用配置值）。
    返回:
        文本增量流。
    """
    temp = settings.llm_temperature if temperature is None else temperature
    tokens = settings.llm_max_tokens if max_tokens is None else max_tokens
    async for delta in _STREAMER(messages, settings, temp, tokens):
        yield delta


# endregion
# ============================================
