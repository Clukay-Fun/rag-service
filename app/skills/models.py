"""
Skill 输入输出数据模型定义。
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# ============================================
# region 数据模型
# ============================================
class SkillInput(BaseModel):
    query: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False


class SkillOutput(BaseModel):
    content: str
    latency_ms: float
    metadata: Dict[str, Any] = {}
# endregion
# ============================================
