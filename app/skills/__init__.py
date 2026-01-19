"""
Skills 包：集中导出注册中心与已注册技能。
"""

from app.skills.registry import registry, register_skill
from app.skills.chat import GreetingSkill, HelpSkill, ChitchatSkill

__all__ = [
    "registry",
    "register_skill",
    "GreetingSkill",
    "HelpSkill",
    "ChitchatSkill",
]
