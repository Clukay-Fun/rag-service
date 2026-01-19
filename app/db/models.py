"""
文件名: models.py
描述: 定义 RAG Service 使用的核心数据库模型。
主要功能:
    - 文档表 Document，存储向量、内容及元数据
依赖: sqlalchemy, pgvector, app.config, app.db.database
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from pgvector.sqlalchemy import Vector

from app.config import EMBEDDING_DIM, RAG_SCHEMA
from app.db.database import Base


# ============================================
# region 模型定义
# ============================================
class Document(Base):
    """向量化文档模型。"""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_collection", "collection"),
        Index("ix_documents_source_id", "source_id"),
        Index("ix_documents_created_at", "created_at"),
        {"schema": RAG_SCHEMA},
    )

    id = Column(Integer, primary_key=True, index=True)
    collection = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    doc_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """转为可序列化字典。"""
        return {
            "id": self.id,
            "collection": self.collection,
            "source_id": self.source_id,
            "content": self.content,
            "metadata": self.doc_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
# endregion
# ============================================
