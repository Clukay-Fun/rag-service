# RAG 服务

基于 FastAPI 构建的检索增强生成（RAG）服务，支持文档索引、语义搜索和向量检索。

## 🚀 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL（带 pgvector 扩展）
- Redis（可选，用于缓存）

### 安装步骤

1. **克隆项目并安装依赖**
```bash
cd E:\.Program\Python\rag-service
pip install -r requirements.txt
```

2. **环境配置**
复制 `.env.example` 为 `.env` 并修改配置：
```bash
cp .env.example .env
```

3. **启动服务**
```bash
uvicorn app.main:app --reload --port 8001
```

服务将在 `http://localhost:8001` 启动，访问 `http://localhost:8001/docs` 查看 API 文档。

## 📁 项目结构

```
rag-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库连接
│   ├── models.py            # 数据模型
│   ├── embedding.py         # 向量生成
│   ├── retriever.py         # 检索逻辑
│   └── search.py            # API 接口
├── requirements.txt         # 依赖包
├── .env                    # 环境变量
└── README.md              # 说明文档
```

## 🔧 核心功能

### 文档索引
- 支持文本、PDF、Word 等格式文档
- 自动分块和向量化
- 元数据存储（来源、时间、作者等）

### 语义搜索
- 基于向量相似度的语义检索
- 支持混合搜索（关键词 + 语义）
- 结果重排序（Rerank）

### 数据集管理
- 多数据集支持
- 文档增删改查
- 批量操作

## 📡 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/search/` | 语义搜索 |
| POST | `/api/v1/search/index` | 文档索引 |
| DELETE | `/api/v1/search/{collection}` | 删除数据集 |
| GET | `/api/v1/search/collections` | 列出数据集 |
| GET | `/health` | 健康检查 |

### 搜索示例
```bash
curl -X POST "http://localhost:8001/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是人工智能",
    "top_k": 5,
    "collection": "default"
  }'
```

### 索引文档示例
```bash
curl -X POST "http://localhost:8001/api/v1/search/index" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "人工智能是计算机科学的一个分支...",
        "metadata": {
          "title": "AI介绍",
          "source": "wikipedia"
        }
      }
    ],
    "collection": "default"
  }'
```

## ⚙️ 配置说明

### 环境变量
```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# 向量模型
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# 重排序模型（可选）
RERANK_MODEL_NAME=BAAI/bge-reranker-base

# Redis 缓存（可选）
REDIS_URL=redis://localhost:6379/0
```

### 模型配置
支持多种嵌入模型：
- OpenAI: `text-embedding-3-small`, `text-embedding-3-large`
- 本地模型: `BAAI/bge-small-zh-v1.5`

## 🛠️ 开发说明

### 添加新功能
1. 在 `models.py` 中定义数据模型
2. 在 `retriever.py` 中实现检索逻辑
3. 在 `search.py` 中添加 API 端点
4. 更新 `main.py` 注册路由

### 运行测试
```bash
# 启动测试数据库
docker-compose -f docker-compose.test.yml up -d

# 运行测试
pytest tests/
```

## 🔍 性能优化

- 向量检索使用 pgvector 索引加速
- 支持 Redis 查询缓存
- 批处理文档向量化
- 异步 API 处理

## 🐛 故障排除

### 常见问题
1. **数据库连接失败**
   - 检查 PostgreSQL 服务状态
   - 验证 `DATABASE_URL` 配置

2. **向量模型加载失败**
   - 检查网络连接（在线模型）
   - 验证模型文件路径（本地模型）

3. **内存不足**
   - 减少批处理大小
   - 使用较小的嵌入模型

### 日志查看
```bash
# 查看服务日志
uvicorn app.main:app --reload --port 8001 --log-level debug
```

## 📈 监控指标

服务提供 Prometheus 指标端点：
- `/metrics` - 性能指标
- 请求计数、响应时间、错误率等

## 📄 许可证

MIT License

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 项目仓库: [https://github.com/yourusername/rag-service](https://github.com/yourusername/rag-service)

---

**版本**: 1.0.0  
**最后更新**: 2026年1月  
**状态**: 🟢 生产就绪
