"""
RAG data models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from pgvector.sqlalchemy import Vector

from app.config import EMBEDDING_DIM, RAG_SCHEMA
from app.db.database import Base


# ============================================
# region 数据库
# ============================================
class Document(Base):
    """
    Generic vector document.
    """
    __tablename__ = "documents"
    __table_args__ = {"schema": RAG_SCHEMA}

    id = Column(Integer, primary_key=True, index=True)
    collection = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    doc_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
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
