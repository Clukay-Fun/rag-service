"""
检索技能：根据关键词判断集合，调用混合检索并返回文本结果。
"""

import asyncio
from typing import List, Optional, Tuple

from app.skills.base import BaseSkill, SkillCategory
from app.skills.models import SkillInput, SkillOutput
from app.skills.registry import register_skill
from app.services.retriever import hybrid_search
from app.db.database import SessionLocal


# ============================================
# region 内部工具
# ============================================
CollectionRule = Tuple[str, List[str]]

COLLECTION_RULES: List[CollectionRule] = [
    ("performances", ["业绩", "项目", "案例", "performance", "project"]),
    ("contracts", ["合同", "条款", "contract"]),
    ("enterprises", ["企业", "公司", "供应商", "enterprise", "company", "vendor"]),
    ("lawyers", ["律师", "法律顾问", "lawyer"]),
]


def pick_collection(query: str) -> Optional[str]:
    q = query.lower()
    for collection, keys in COLLECTION_RULES:
        if any(k.lower() in q for k in keys):
            return collection
    return None
# endregion
# ============================================


# ============================================
# region Skill
# ============================================
def clean_query_text(query: str) -> str:
    cleaned = query
    for token in ["查询", "搜索", "查找"]:
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip()
    return cleaned or query


@register_skill
class SearchSkill(BaseSkill):
    name = "search_skill"
    description = "根据用户问题检索业绩、合同、企业或律师信息。"
    category = SkillCategory.SEARCH
    keywords = ["查询", "搜索", "查找", "业绩", "合同", "企业", "律师", "performance", "contract", "enterprise", "lawyer"]

    async def execute(self, input_data: SkillInput) -> SkillOutput:
        collection = pick_collection(input_data.query)
        if not collection:
            return SkillOutput(
                content="未识别到检索类别，请包含关键词：业绩/合同/企业/律师。",
                latency_ms=0,
                metadata={},
            )

        # 调用同步检索函数放入线程，避免阻塞事件循环
        loop = asyncio.get_running_loop()

        def _run_search():
            db = SessionLocal()
            try:
                return hybrid_search(
                    db=db,
                    query=clean_query_text(input_data.query),
                    collection=collection,
                    top_k=5,
                    rerank_top_k=5,
                    use_rerank=False,
                )
            finally:
                db.close()

        results = await loop.run_in_executor(
            None,
            _run_search,
        )

        lines = []
        for idx, item in enumerate(results[:5], 1):
            title = item.get("metadata", {}).get("title") or item.get("content", "")[:50]
            lines.append(f"{idx}. {title}")

        if not lines:
            content = f"未找到相关结果（类别：{collection}）。"
        else:
            content = f"检索结果（类别：{collection}）：\n" + "\n".join(lines)

        return SkillOutput(
            content=content,
            latency_ms=0,
            metadata={"collection": collection},
        )
# endregion
# ============================================
