"""
RAG service configuration.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# region 数据库
# ============================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/bidding_assistant",
)
RAG_SCHEMA = "rag"
# endregion
# ============================================

# ============================================
# region API
# ============================================
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv(
    "SILICONFLOW_BASE_URL",
    "https://api.siliconflow.cn/v1",
)
# endregion
# ============================================

# ============================================
# region 模型
# ============================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
CHAT_MODEL = os.getenv("CHAT_MODEL", "internlm/internlm2_5-7b-chat")
# endregion
# ============================================

# ============================================
# region 检索
# ============================================
VECTOR_TOP_K = 10
RERANK_TOP_K = 3
SIMILARITY_THRESHOLD = 0.5
# endregion
# ============================================

# ============================================
# region 检索
# ============================================
KEYWORD_SEARCH_ENABLED = True
KEYWORD_TOP_K = 10
KEYWORD_TSVECTOR_COLLECTIONS = {"performances", "contracts"}
KEYWORD_ILIKE_COLLECTIONS = {"enterprises", "lawyers"}
TRGM_SIMILARITY_THRESHOLD = 0.1
# endregion
# ============================================

# ============================================
# region 缓存
# ============================================
REDIS_URL = os.getenv("REDIS_URL", "")
CACHE_TTL = 300
# endregion
# ============================================
