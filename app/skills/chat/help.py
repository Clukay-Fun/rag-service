"""
帮助技能：提供功能列表与使用提示。
"""

import time

from app.skills.base import BaseSkill, SkillCategory
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import register_skill


# ============================================
# region Skill
# ============================================
@register_skill
class HelpSkill(BaseSkill):
    name = "help_skill"
    description = "Provide usage guidance and feature list."
    category = SkillCategory.CHAT
    keywords = ["帮助", "怎么用", "功能", "help"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start = time.perf_counter()
        content = (
            "我可以帮你做这些：\n"
            "1) 查询业绩/企业/律师信息\n"
            "2) 合同条款与风险分析\n"
            "3) 文档信息提取与汇总\n"
            "请告诉我你的具体需求。"
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return SkillOutput(content=content, latency_ms=latency_ms)
# endregion
# ============================================
