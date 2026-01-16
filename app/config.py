"""
RAG 服务配置
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 数据库配置 (共用 PostgreSQL，独立 Schema)
# ============================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/bidding_assistant"
)
RAG_SCHEMA = "rag"  # RAG 服务独立 schema

# ============================================
# SiliconFlow API 配置
# ============================================
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.getenv(
    "SILICONFLOW_BASE_URL",
    "https://api.siliconflow.cn/v1"
)

# ============================================
# 模型配置
# ============================================
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# ============================================
# 检索配置
# ============================================
VECTOR_TOP_K = 10           # 向量检索数量
RERANK_TOP_K = 3            # Rerank 后保留数量
SIMILARITY_THRESHOLD = 0.5  # 相似度阈值

# ============================================
# 缓存配置 (可选 Redis)
# ============================================
REDIS_URL = os.getenv("REDIS_URL", "")
CACHE_TTL = 300  # 缓存 5 分钟
