"""
分析技能：调用对话模型，针对合同/风险/标书等问题给出简要分析。
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
class AnalysisSkill(BaseSkill):
    name = "analysis_skill"
    description = "合同/风险/标书等问题的简要分析。"
    category = SkillCategory.ANALYSIS
    keywords = ["分析", "风险", "合同", "审查", "评估", "标书", "tender", "risk", "contract"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start = time.perf_counter()
        prompt = (
            "你是招投标与合同风险分析助手，请简洁回答关键风险与建议。\n"
            f"用户问题：{input_data.query}\n"
            "请输出：主要风险/关注点 + 简短建议。"
        )
        content = await chat_completion(prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return SkillOutput(content=content, latency_ms=latency_ms, metadata={})
# endregion
# ============================================
