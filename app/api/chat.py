"""
聊天接口：路由到对应技能并返回回复。
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.orchestrator.router import SkillRouter
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import registry
import app.skills  # noqa: F401


# ============================================
# region 路由
# ============================================
router = APIRouter(prefix="/chat", tags=["chat"])
skill_router = SkillRouter()
# endregion
# ============================================


# ============================================
# region 请求模型
# ============================================
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str | None = None
# endregion
# ============================================


# ============================================
# region 响应模型
# ============================================
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
async def chat(request: ChatRequest):
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
