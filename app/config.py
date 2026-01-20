"""
文件名: config.py
描述: RAG 服务的配置加载模块。
主要功能:
    - 加载并规范化 RAG_ 前缀环境变量。
    - 提供可缓存的 Settings 对象用于依赖注入。
依赖: python-dotenv
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# ============================================
# region 环境变量辅助
# ============================================
def _get_int_env(name: str, default: int) -> int:
    """
    读取整数类型环境变量，失败时使用默认值。

    参数:
        name: 环境变量名。
        default: 缺失或非法时的默认值。
    返回:
        解析后的整数值。
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default

def _get_str_env(name: str, default: str) -> str:
    """
    读取字符串类型环境变量，失败时使用默认值。

    参数:
        name: 环境变量名。
        default: 缺失时的默认值。
    返回:
        环境变量字符串值。
    """
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value

def _resolve_database_url() -> str:
    """
    从 RAG_DATABASE_URL 或 DATABASE_URL 解析数据库地址。

    返回:
        数据库连接字符串。
    """
    rag_url = os.getenv("RAG_DATABASE_URL")
    if rag_url:
        return rag_url
    legacy_url = os.getenv("DATABASE_URL")
    if legacy_url:
        return legacy_url
    return "postgresql://postgres:postgres@localhost:5432/rag_service"


# endregion
# ============================================

# ============================================
# region 配置模型
# ============================================
@dataclass(frozen=True)
class Settings:
    """
    服务运行所需的不可变配置项。
    """

    database_url: str
    max_document_size: int
    max_top_k: int
    max_rerank_candidates: int
    hnsw_ef_search: int
    chunk_size: int
    chunk_overlap: int
    embedding_dim: int
    log_level: str


@lru_cache
def get_settings() -> Settings:
    """
    从环境变量加载配置并缓存结果。

    返回:
        Settings 实例。
    """
    load_dotenv()
    return Settings(
        database_url=_resolve_database_url(),
        max_document_size=_get_int_env("RAG_MAX_DOCUMENT_SIZE", 50 * 1024 * 1024),
        max_top_k=_get_int_env("RAG_MAX_TOP_K", 20),
        max_rerank_candidates=_get_int_env("RAG_MAX_RERANK_CANDIDATES", 100),
        hnsw_ef_search=_get_int_env("RAG_HNSW_EF_SEARCH", 40),
        chunk_size=_get_int_env("RAG_CHUNK_SIZE", 512),
        chunk_overlap=_get_int_env("RAG_CHUNK_OVERLAP", 64),
        embedding_dim=_get_int_env("RAG_EMBEDDING_DIM", 1024),
        log_level=_get_str_env("RAG_LOG_LEVEL", "INFO"),
    )


# endregion
# ============================================
