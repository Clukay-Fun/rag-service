"""
路由规则：定义关键词模式与优先级。
"""


# ============================================
# region 路由
# ============================================
ROUTING_RULES = [
    {
        "patterns": ["你好", "您好", "hi", "hello"],
        "skill": "greeting_skill",
        "priority": 100,
    },
    {
        "patterns": ["帮助", "怎么用", "功能", "help"],
        "skill": "help_skill",
        "priority": 95,
    },
    {
        "patterns": ["业绩", "项目", "案例", "performance", "project"],
        "skill": "performance_search_skill",
        "priority": 92,
    },
    {
        "patterns": ["企业", "公司", "供应商", "enterprise", "company", "vendor"],
        "skill": "enterprise_search_skill",
        "priority": 91,
    },
    {
        "patterns": ["律师", "法律顾问", "lawyer"],
        "skill": "lawyer_search_skill",
        "priority": 90,
    },
    {
        "patterns": ["分析", "评估", "审查", "风险", "标书", "tender", "contract", "risk"],
        "skill": "analysis_skill",
        "priority": 85,
    },
    {
        "patterns": ["提取", "识别", "解析", "抽取", "extract"],
        "skill": "extraction_skill",
        "priority": 82,
    },
    {
        "patterns": ["查询", "搜索", "查找", "performance", "contract", "enterprise", "lawyer"],
        "skill": "search_skill",
        "priority": 80,
    },
]
# endregion
# ============================================
