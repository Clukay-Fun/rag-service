---
name: rag-service-backend
description: "Python 3.11+ FastAPI + PostgreSQL/pgvector backend for RAG Service; use when adding/updating APIs, services, DB models, schemas, tests, or infra. Enforce file-head docstrings, simple RAG pipeline (no Redis), and clean layering (api/services/db)."
---

# RAG Service Backend Skill

Use this skill when修改/新增 RAG Service 后端代码（FastAPI + PostgreSQL + pgvector + SQLAlchemy）。目标：保持简单、可维护、无 Redis 依赖。

## 开发约定
- Python 3.11+；依赖管理：requirements.txt。
- 每个 Python 文件首行添加三引号注释，说明文件名、用途、主要功能、依赖。
- 目录分层：`api/` 路由、`services/` 业务、`db/` 连接与模型、`schemas/` Pydantic。
- 类型提示必填；避免全局 Session，使用依赖注入/上下文管理。
- 数据库存储：PostgreSQL + pgvector，默认向量维度 1024，余弦相似度。
- 不使用 Redis；缓存暂缓。
- 使用 region 注释划分代码区域：
```python
# ============================================
# region 区域名称
# ============================================

# 这里是代码...

# endregion
# ============================================
```
- 函数/类注释
```python
def function_name(param: str) -> dict:
    """
    函数功能简述
    
    参数:
        param: 参数说明
    返回:
        返回值说明
    """
    pass
```
- 每次开发完成后
更新 README.md 的开发进度
提供测试代码验证功能
- 测试代码格式
```python
# tests/test_xxx.py
"""
测试: xxx 功能
运行: python -m pytest tests/test_xxx.py -v
"""

def test_功能名称():
    """测试说明"""
    # 测试代码
    assert 结果 == 预期
```
- README 更新格式
```python
## 开发进度

### ✅ 已完成
- [x] 功能1 - 简述
- [x] 功能2 - 简述

### 🚧 进行中
- [ ] 功能3

### 📋 待开发
- [ ] 功能4
```
## 输出要求
代码必须符合上述规范
每次输出完整可运行的代码
附带对应的测试代码
说明 README.md 需要更新的内容
```python

---

## 二、快捷指令

在对话中使用这些指令快速触发特定行为：

| 指令 | 作用 |
|------|------|
| `/new 文件名` | 创建新文件，包含标准头部注释 |
| `/test` | 为刚写的代码生成测试 |
| `/readme` | 生成 README 更新内容 |
| `/check` | 检查代码是否符合规范 |
| `/region 名称` | 生成 region 代码块模板 |

---

## 三、示例对话

### 你说：
```
## 常用流程
- **新接口**：定义请求/响应 Schema → 编写 service 逻辑 → 路由中依赖注入 db/session → 补测试。
- **新增模型**：在 `db/models.py` 定义 SQLAlchemy 模型（含 pgvector 列/索引），在 CRUD 或 service 层添加方法；迁移脚本或 init SQL 保持同步。
- **向量检索**：分块 → bge-m3 向量化 → pgvector 相似度搜索 →（可选）bge-reranker 精排；确保 chunk_size/overlap 可配置。
- **配置**：集中于 `config.py`，暴露 chunk_size、overlap、top_k、threshold、embedding_dim 等；加载 `.env`。

## 代码模式
- **DB 连接**：`SessionLocal = sessionmaker(...)`; 在依赖函数中 `with SessionLocal() as session: yield session`，确保提交/回滚/关闭。
- **错误处理**：FastAPI HTTPException，记录日志；对外隐藏内部错误细节。
- **文件头模板**：
  ```python
  """
  文件名: xxx.py
  描述: 简述职责
  主要功能:
      - 功能1
      - 功能2
  依赖: 关键依赖
  """
  ```
- **测试**：优先覆盖 上传→入库→检索 回环；使用 TestClient + 临时数据库/事务回滚。

## 提示
- 保持最小依赖；不引入消息队列/缓存层。
- 面向外部应用（如投标助手）暴露清晰的 HTTP API；保持响应结构稳定。
- 记录 README 的改动与计划，CODEX.md 不再使用。
