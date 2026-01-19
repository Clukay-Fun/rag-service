"""
闲聊技能：调用对话模型输出自然语言回复。
"""

import time

from app.skills.base import BaseSkill, SkillCategory
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import register_skill
from app.services.llm import chat_completion


# ============================================
# region Skill
# ============================================
@register_skill
class ChitchatSkill(BaseSkill):
    name = "chitchat_skill"
    description = "General conversation and small talk."
    category = SkillCategory.CHAT
    keywords = []

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start = time.perf_counter()
        content = await chat_completion(input_data.query)
        latency_ms = (time.perf_counter() - start) * 1000
        return SkillOutput(content=content, latency_ms=latency_ms)
# endregion
# ============================================
