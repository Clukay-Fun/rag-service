"""
文件名: main.py
描述: FastAPI 入口，负责应用生命周期、路由注册与基础中间件。
主要功能:
    - 初始化数据库与 schema
    - 配置 CORS
    - 注册业务路由（搜索、聊天路由器）
依赖: fastapi, sqlalchemy
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db, ensure_indexes, engine
from app.db.models import Base
from app.api import search, chat


# ============================================
# region 应用生命周期
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用启动与关闭阶段。"""
    print("RAG Service 正在启动...")
    init_db()
    Base.metadata.create_all(bind=engine)
    ensure_indexes()
    print("RAG Service 启动完成。")

    yield

    print("RAG Service 已关闭。")
# endregion
# ============================================


# ============================================
# region 应用配置
# ============================================
app = FastAPI(
    title="RAG Service",
    description="独立的向量检索与语义搜索服务，支持可选 rerank。",
    version="1.0.0",
    lifespan=lifespan,
)

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
async def health_check() -> dict:
    """健康检查接口。"""
    return {"status": "healthy", "service": "rag"}
# endregion
# ============================================
