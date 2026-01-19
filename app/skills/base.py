"""
Skill 基类定义，包含通用元数据与匹配逻辑。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

from app.skills.models import SkillInput, SkillOutput


# ============================================
# region Skill
# ============================================
class SkillCategory(str, Enum):
    CHAT = "chat"
    SEARCH = "search"
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    REPORT = "report"


class BaseSkill(ABC):
    name: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.CHAT
    required_model: Optional[str] = None
    keywords: List[str] = []

    @abstractmethod
    async def execute(self, input_data: SkillInput) -> SkillOutput:
        raise NotImplementedError

    def matches_rule(self, query: str) -> bool:
        return any(kw in query for kw in self.keywords)

    def keyword_score(self, query: str) -> float:
        if not self.keywords:
            return 0.0
        hit = sum(1 for kw in self.keywords if kw in query)
        return hit / len(self.keywords)
# endregion
# ============================================
