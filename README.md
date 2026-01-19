# RAG Service

独立的 RAG 检索服务（FastAPI + PostgreSQL + pgvector），供投标助手等上层应用复用。项目聚焦 RAG 管线，移除 Redis，保持简单可维护。

---

## 快速开始
1) 安装依赖
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2) 配置环境变量（`.env`）
```ini
# 数据库
DATABASE_URL=postgresql://postgres:password@localhost:5432/rag_service
RAG_SCHEMA=rag

# 模型与服务
SILICONFLOW_API_KEY=sk-xxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
RERANK_MODEL=BAAI/bge-reranker-v2-m3

# 分块与检索
CHUNK_SIZE=500
CHUNK_OVERLAP=50
VECTOR_TOP_K=10
RERANK_TOP_K=3
SIMILARITY_THRESHOLD=0.5
KEYWORD_SEARCH_ENABLED=true
KEYWORD_TOP_K=10
TRGM_SIMILARITY_THRESHOLD=0.1
```

3) 运行
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
Docs: `http://localhost:8001/docs`

---

## 目录结构
```
app/
├── api/                # 路由层
├── db/                 # Engine/Session/Models
├── services/           # embedding / retriever
├── orchestrator/       # 技能路由
├── main.py             # FastAPI 入口
└── config.py           # 全局配置
tests/
```

---

## API 概览
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/search/` | 语义搜索（可选 rerank） |
| POST | `/api/v1/search/index` | 文档批量入库 |
| DELETE | `/api/v1/search/{collection}` | 删除集合 |
| GET | `/api/v1/search/collections` | 集合列表 |
| POST | `/api/v1/chat/` | 聊天路由到技能 |
| GET | `/health` | 健康检查 |

示例：
```bash
curl -X POST "http://localhost:8001/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{ "query": "招标文件的评标标准是什么", "top_k": 5, "collection": "default" }'
```

---

## 开发进度

### ✅ 已完成
- [x] 基础配置清理：移除 Redis 配置、集中检索/分块超参
- [x] 入口与核心模块文件头注释、UTF-8 清理

### 🚧 进行中
- [ ] 检索/向量化流程优化与健壮性加强
- [ ] API 返回结构与错误处理统一

### 📝 待开发
- [ ] 上传→检索 回环集成测试
- [ ] 分块与文档解析流程实现
- [ ] 部署脚本与示例客户端

---

## 许可证
MIT
