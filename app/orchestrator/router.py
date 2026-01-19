"""
技能路由器：按规则匹配选择技能，默认回退到闲聊。
"""

import time
from dataclasses import dataclass
from typing import Optional

from app.orchestrator.rules import ROUTING_RULES
from app.skills.registry import registry


# ============================================
# region 路由
# ============================================
@dataclass
class RoutingResult:
    skill_name: str
    method: str
    latency_ms: float


class SkillRouter:
    def __init__(self, default_skill: str = "chitchat_skill") -> None:
        self.default_skill = default_skill

    async def route(self, query: str) -> RoutingResult:
        start = time.perf_counter()
        matched = self._match_rules(query)
        if matched:
            return RoutingResult(
                skill_name=matched,
                method="rule",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        return RoutingResult(
            skill_name=self.default_skill,
            method="default",
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    def _match_rules(self, query: str) -> Optional[str]:
        rules = sorted(ROUTING_RULES, key=lambda r: r["priority"], reverse=True)
        for rule in rules:
            if any(pattern in query for pattern in rule["patterns"]):
                if rule["skill"] in [s.name for s in registry.all()]:
                    return rule["skill"]
        return None
# endregion
# ============================================
