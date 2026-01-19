"""
具体检索技能：按集合固定到业绩/企业/律师/语义等。
"""

import asyncio
from typing import List

from app.skills.base import BaseSkill, SkillCategory
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import register_skill
from app.services.retriever import hybrid_search
from app.db.database import SessionLocal
from app.skills.search import clean_query_text


# ============================================
# region 公共执行器
# ============================================
async def run_collection_search(
    query: str,
    collection: str,
    top_k: int = 5,
    rerank_top_k: int = 5,
    use_rerank: bool = False,
) -> List[dict]:
    loop = asyncio.get_running_loop()

    def _do():
        db = SessionLocal()
        try:
            return hybrid_search(
                db=db,
                query=query,
                collection=collection,
                top_k=top_k,
                rerank_top_k=rerank_top_k,
                use_rerank=use_rerank,
            )
        finally:
            db.close()

    return await loop.run_in_executor(None, _do)
# endregion
# ============================================


# ============================================
# region 具体技能
# ============================================
@register_skill
class PerformanceSearchSkill(BaseSkill):
    name = "performance_search_skill"
    description = "查询业绩/项目案例"
    category = SkillCategory.SEARCH
    keywords = ["业绩", "项目", "案例", "performance", "project"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        results = await run_collection_search(clean_query_text(input_data.query), "performances")
        if not results:
            return SkillOutput(content="未找到相关业绩。", latency_ms=0, metadata={})
        lines = [f"{i+1}. {r.get('metadata',{}).get('title') or r.get('content','')[:50]}" for i, r in enumerate(results[:5])]
        return SkillOutput(content="业绩检索结果：\n" + "\n".join(lines), latency_ms=0, metadata={"collection": "performances"})


@register_skill
class EnterpriseSearchSkill(BaseSkill):
    name = "enterprise_search_skill"
    description = "查询企业/供应商信息"
    category = SkillCategory.SEARCH
    keywords = ["企业", "公司", "供应商", "enterprise", "company", "vendor"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        results = await run_collection_search(clean_query_text(input_data.query), "enterprises")
        if not results:
            return SkillOutput(content="未找到相关企业。", latency_ms=0, metadata={})
        lines = [f"{i+1}. {r.get('metadata',{}).get('name') or r.get('content','')[:50]}" for i, r in enumerate(results[:5])]
        return SkillOutput(content="企业检索结果：\n" + "\n".join(lines), latency_ms=0, metadata={"collection": "enterprises"})


@register_skill
class LawyerSearchSkill(BaseSkill):
    name = "lawyer_search_skill"
    description = "查询律师/法律顾问信息"
    category = SkillCategory.SEARCH
    keywords = ["律师", "法律顾问", "lawyer"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        results = await run_collection_search(clean_query_text(input_data.query), "lawyers")
        if not results:
            return SkillOutput(content="未找到相关律师。", latency_ms=0, metadata={})
        lines = [f"{i+1}. {r.get('metadata',{}).get('name') or r.get('content','')[:50]}" for i, r in enumerate(results[:5])]
        return SkillOutput(content="律师检索结果：\n" + "\n".join(lines), latency_ms=0, metadata={"collection": "lawyers"})


@register_skill
class SemanticSearchSkill(BaseSkill):
    name = "semantic_search_skill"
    description = "通用语义搜索（未指定集合时）"
    category = SkillCategory.SEARCH
    keywords = ["搜索", "查询", "找", "search"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        results = await run_collection_search(clean_query_text(input_data.query), "contracts")
        if not results:
            return SkillOutput(content="未找到相关结果。", latency_ms=0, metadata={})
        lines = [f"{i+1}. {r.get('metadata',{}).get('title') or r.get('content','')[:50]}" for i, r in enumerate(results[:5])]
        return SkillOutput(content="通用检索结果：\n" + "\n".join(lines), latency_ms=0, metadata={"collection": "contracts"})
# endregion
# ============================================
