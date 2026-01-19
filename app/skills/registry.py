"""
Skill 注册中心，负责技能注册与查找。
"""

from typing import Dict, List, Type

from app.skills.base import BaseSkill


# ============================================
# region Skill
# ============================================
class SkillRegistry:
    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill_cls: Type[BaseSkill]) -> Type[BaseSkill]:
        instance = skill_cls()
        if not instance.name:
            raise ValueError("Skill name is required")
        self._skills[instance.name] = instance
        return skill_cls

    def get(self, name: str) -> BaseSkill:
        return self._skills[name]

    def all(self) -> List[BaseSkill]:
        return list(self._skills.values())


registry = SkillRegistry()


def register_skill(skill_cls: Type[BaseSkill]) -> Type[BaseSkill]:
    return registry.register(skill_cls)
# endregion
# ============================================
