"""
RAG 服务数据模型
通用向量文档模型，支持多种数据集
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from pgvector.sqlalchemy import Vector

from app.config import EMBEDDING_DIM, RAG_SCHEMA
from app.db.database import Base


# ============================================
# region 向量文档模型
# ============================================

class Document(Base):
    """
    通用向量文档
    支持存储任意类型的文档及其向量
    """
    __tablename__ = "documents"
    __table_args__ = {"schema": RAG_SCHEMA}
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 数据集标识（如 performances, lawyers, enterprises）
    collection = Column(String(50), nullable=False, index=True)
    
    # 原始数据 ID（关联到业务表）
    source_id = Column(Integer, nullable=True, index=True)
    
    # 文档内容
    content = Column(Text, nullable=False)
    
    # 向量嵌入
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    
    # 元数据（存储额外信息）
    doc_metadata = Column(JSON, default={})
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
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
