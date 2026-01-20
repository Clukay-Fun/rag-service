"""
文件名: database.py
描述: 数据库引擎与会话管理。
主要功能:
    - 创建 SQLAlchemy 引擎与会话工厂。
    - 提供数据库依赖注入与初始化入口。
依赖: SQLAlchemy, python-dotenv
"""

from __future__ import annotations

from functools import lru_cache
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

# ============================================
# region 引擎与会话工厂
# ============================================


def _create_engine(database_url: str) -> Engine:
    """
    创建 SQLAlchemy 引擎。

    参数:
        database_url: 数据库连接字符串。
    返回:
        SQLAlchemy Engine。
    """
    return create_engine(database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_engine(database_url: Optional[str] = None) -> Engine:
    """
    获取（并缓存）数据库引擎。

    参数:
        database_url: 可选数据库连接字符串。
    返回:
        SQLAlchemy Engine。
    """
    resolved_url = database_url or get_settings().database_url
    return _create_engine(resolved_url)


@lru_cache
def get_session_factory(database_url: Optional[str] = None) -> sessionmaker:
    """
    获取（并缓存）Session 工厂。

    参数:
        database_url: 可选数据库连接字符串。
    返回:
        SQLAlchemy sessionmaker。
    """
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


# endregion
# ============================================

# ============================================
# region 依赖注入与初始化
# ============================================


def get_db(database_url: Optional[str] = None) -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）。

    参数:
        database_url: 可选数据库连接字符串。
    返回:
        Session 生成器。
    """
    session_factory = get_session_factory(database_url)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_db(database_url: Optional[str] = None) -> None:
    """
    初始化数据库结构与扩展。

    参数:
        database_url: 可选数据库连接字符串。
    """
    engine = get_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=connection)


# endregion
# ============================================
