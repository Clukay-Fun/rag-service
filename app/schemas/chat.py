"""
文件名: chat.py
描述: 流式对话请求模型。
主要功能:
    - 定义流式对话的请求 Schema。
依赖: pydantic
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

# ============================================
# region 请求模型
# ============================================


class ChatMessage(BaseModel):
    """对话消息。"""

    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatStreamRequest(BaseModel):
    """流式对话请求。"""

    query: str = Field(..., min_length=1)
    knowledge_base_id: int = Field(..., gt=0)
    top_k: int = Field(default=5, ge=1)
    history: Optional[List[ChatMessage]] = None


# endregion
# ============================================
