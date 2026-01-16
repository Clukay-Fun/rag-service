"""
RAG 服务数据库连接
共用 PostgreSQL，使用独立 Schema
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL, RAG_SCHEMA


# ============================================
# region 数据库引擎
# ============================================

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# endregion
# ============================================


# ============================================
# region 数据库初始化
# ============================================

def init_db():
    """初始化数据库：创建 schema 和启用 pgvector"""
    with engine.connect() as conn:
        # 创建独立 schema
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {RAG_SCHEMA}"))
        
        # 启用 pgvector 扩展
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        conn.commit()
        print(f"✅ RAG Schema '{RAG_SCHEMA}' 已就绪")


def get_db():
    """获取数据库会话（FastAPI 依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# endregion
# ============================================
