"""
RAG 服务入口
独立的向量检索服务，供多个助手调用
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db, engine
from app.db.models import Base
from app.api import search, chat


# ============================================
# region 应用生命周期
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 RAG 服务启动中...")
    init_db()
    Base.metadata.create_all(bind=engine)
    print("✅ RAG 服务已就绪")
    
    yield
    
    # 关闭时
    print("👋 RAG 服务关闭")

# endregion
# ============================================


# ============================================
# region 应用配置
# ============================================

app = FastAPI(
    title="RAG Service",
    description="向量检索服务 - 支持语义搜索、Rerank、文档索引",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# endregion
# ============================================


# ============================================
# region 路由注册
# ============================================

app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

# endregion
# ============================================


# ============================================
# region 健康检查
# ============================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "rag"}

# endregion
# ============================================
