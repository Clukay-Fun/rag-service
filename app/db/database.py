"""
RAG database connection and initialization.
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
# region 数据库
# ============================================
def init_db() -> None:
    """Initialize schema, extensions, and indexes."""
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {RAG_SCHEMA}"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

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
# region 数据库
# ============================================
def get_db():
    """Yield DB session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# endregion
# ============================================
