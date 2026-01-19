"""
文件名: chat.py
描述: 聊天路由，负责将用户输入路由至技能并返回回复。
主要功能:
    - 接收聊天请求
    - 调用技能路由器选择技能
    - 返回技能执行结果
依赖: fastapi, pydantic, app.orchestrator, app.skills
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.orchestrator.router import SkillRouter
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import registry
import app.skills  # noqa: F401  # 确保技能注册


# ============================================
# region 路由
# ============================================
router = APIRouter(prefix="/chat", tags=["chat"])
skill_router = SkillRouter()
# endregion
# ============================================


# ============================================
# region 请求/响应模型
# ============================================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    skill_used: str
    routing_method: str
    latency_ms: float
# endregion
# ============================================


# ============================================
# region API
# ============================================
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """聊天入口，自动路由到技能并返回结果。"""
    routing = await skill_router.route(request.message)
    skill = registry.get(routing.skill_name)
    result: SkillOutput = await skill.execute(
        SkillInput(query=request.message, user_id=request.user_id)
    )
    return ChatResponse(
        message=result.content,
        skill_used=routing.skill_name,
        routing_method=routing.method,
        latency_ms=result.latency_ms,
    )
# endregion
# ============================================
