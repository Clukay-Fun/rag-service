"""
问候技能：快速返回模板问候语。
"""

import random
import time

from app.skills.base import BaseSkill, SkillCategory
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import register_skill


# ============================================
# region Skill
# ============================================
@register_skill
class GreetingSkill(BaseSkill):
    name = "greeting_skill"
    description = "Greeting and welcome messages."
    category = SkillCategory.CHAT
    keywords = ["你好", "您好", "hi", "hello"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start = time.perf_counter()
        replies = [
            "你好！请问需要我帮你做什么？",
            "您好！可以告诉我您的需求。",
            "Hi！我可以协助查询与分析招投标信息。",
        ]
        content = random.choice(replies)
        latency_ms = (time.perf_counter() - start) * 1000
        return SkillOutput(content=content, latency_ms=latency_ms)
# endregion
# ============================================
