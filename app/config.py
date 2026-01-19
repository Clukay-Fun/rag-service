"""
文件名: config.py
描述: 加载并集中管理 RAG Service 的环境配置与默认超参。
主要功能:
    - 读取环境变量和提供默认值
    - 管理数据库、模型、检索与分块参数
    - 约束外部依赖使用
依赖: python-dotenv, os
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# region 数据库
# ============================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/rag_service",
)
RAG_SCHEMA = os.getenv("RAG_SCHEMA", "rag")
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
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
CHAT_MODEL = os.getenv("CHAT_MODEL", "internlm/internlm2_5-7b-chat")
# endregion
# ============================================

# ============================================
# region 分块
# ============================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
# endregion
# ============================================

# ============================================
# region 检索
# ============================================
VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "10"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "3"))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
# endregion
# ============================================

# ============================================
# region 关键词检索
# ============================================
KEYWORD_SEARCH_ENABLED = os.getenv("KEYWORD_SEARCH_ENABLED", "true").lower() == "true"
KEYWORD_TOP_K = int(os.getenv("KEYWORD_TOP_K", "10"))
KEYWORD_TSVECTOR_COLLECTIONS = {"performances", "contracts"}
KEYWORD_ILIKE_COLLECTIONS = {"enterprises", "lawyers"}
TRGM_SIMILARITY_THRESHOLD = float(os.getenv("TRGM_SIMILARITY_THRESHOLD", "0.1"))
# endregion
# ============================================
