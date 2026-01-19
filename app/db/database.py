"""
文件名: database.py
描述: 数据库引擎、Session 工厂及初始化逻辑。
主要功能:
    - 创建 SQLAlchemy Engine 与 SessionLocal
    - 初始化 schema 与 pgvector/pg_trgm 扩展
    - 创建必要的索引（在表创建后执行）
    - 提供 FastAPI 依赖获取数据库会话
依赖: sqlalchemy, app.config
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL, RAG_SCHEMA

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================
# region 数据库初始化
# ============================================
def init_db() -> None:
    """
    初始化数据库 schema 与扩展（不依赖表存在）。

    主要创建:
    - schema: RAG_SCHEMA
    - 扩展: vector, pg_trgm
    """
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {RAG_SCHEMA}"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.commit()


def ensure_indexes() -> None:
    """
    在表创建后调用，确保必要索引存在。

    包括:
    - 向量索引 (hnsw, cosine)
    - 全文索引 (content)
    - 名称 trigram 索引 (metadata->>'name')
    """
    with engine.connect() as conn:
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx
            ON {RAG_SCHEMA}.documents
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))

        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS documents_content_fts_idx
            ON {RAG_SCHEMA}.documents
            USING GIN (to_tsvector('simple', content))
            WHERE collection IN ('performances', 'contracts')
        """))

        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS documents_name_trgm_idx
            ON {RAG_SCHEMA}.documents
            USING GIN (lower(coalesce(doc_metadata->>'name', '')) gin_trgm_ops)
            WHERE collection IN ('enterprises', 'lawyers')
        """))

        conn.commit()
# endregion
# ============================================


# ============================================
# region FastAPI 依赖
# ============================================
def get_db():
    """FastAPI 依赖：提供一个数据库会话，确保关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# endregion
# ============================================
