"""
提取技能：调用对话模型，按提示提取关键信息。
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
class ExtractionSkill(BaseSkill):
    name = "extraction_skill"
    description = "提取合同/业绩/资质等关键信息的简要结构化结果。"
    category = SkillCategory.EXTRACTION
    keywords = ["提取", "识别", "解析", "信息", "数据", "合同", "业绩", "资质", "extract"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        start = time.perf_counter()
        prompt = (
            "你是信息提取助手，请从用户问题中提炼关键信息，输出简短要点列表。\n"
            f"用户问题：{input_data.query}\n"
            "请用简短条目返回要点，不要长篇回答。"
        )
        content = await chat_completion(prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return SkillOutput(content=content, latency_ms=latency_ms, metadata={})
# endregion
# ============================================
