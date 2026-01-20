总览：说明 FastAPI + PostgreSQL/pgvector + BGE-M3 + bge-reranker 组成，强调低延迟、统一 RAG_ 配置前缀、统一错误格式与校验顺序。
架构：分层（API、业务服务、存储），描述知识库/文档/检索流程，并附 Mermaid 流程图。
组件接口：细化 KB CRUD、清理任务、文档上传解析（markitdown+OCR、chunk/embedding 事务）、搜索（top_k 限制、候选数、rerank 返回字段）、监控探针与 metrics。
数据模型：列出 knowledge_bases、documents、document_chunks、cleanup_tasks 主字段与状态枚举，索引/事务约束。
错误处理与测试：统一错误 schema、资源校验顺序、摄取失败回滚；测试覆盖单元/集成/API 契约、性能烟囱、可观测性检查。

按两级编号的可执行步骤覆盖应用骨架、数据模型、知识库 CRUD、清理任务、文档摄取（解析/分块/embedding 事务）、检索+rerank、健康/metrics 以及测试矩阵，并在每步标注对应需求/技术约束。
## 开发进度

### 已完成
- [x] 任务 1 - FastAPI 应用骨架、配置加载、错误 schema、request_id 中间件
完成任务 1 的骨架与基础设施：新增配置加载、统一错误响应、request_id 中间件与结构化请求日志，并预留资源校验顺序的通用校验函数，满足 RAG_ 环境变量约定与错误格式要求。
主要改动集中在基础配置、统一错误响应与请求追踪日志的规范化上，便于后续 API/服务层扩展。
- [x] 任务 2 - 数据模型与迁移
新增数据库层与模型定义、HNSW 索引与初始化入口，并补齐中文注释与单元测试
- [x] 任务 3 - 知识库管理 API
新增知识库业务服务与路由：knowledge_base.py、knowledge_bases.py、knowledge_base.py，覆盖创建/查询/更新/删除/列表与分页过滤。
数据库 JSON 类型兼容测试环境：models.py 将 JSONB 以 JSON 变体形式适配非 PostgreSQL 测试运行。
主应用注册路由：main.py。
- [x] 任务 4 - 清理任务执行器与接口
主要代码新增：cleanup_task.py、cleanup_tasks.py、cleanup_task.py
路由接入：main.py
测试新增：test_cleanup_task_api.py
- [x] 任务 5 - 文档上传与状态查询接口
新增文档上传入口与状态查询接口，包含格式/大小校验、知识库可用性校验、文档记录创建、列表/详情/删除（含 410 语义），并补齐中文注释与单元测试。上传接口使用 app.state.settings 读取 RAG_MAX_DOCUMENT_SIZE，避免运行时缓存错配。

新增接口与服务：documents.py、document.py
新增 Schema：document.py
路由注册：main.py
新增测试：test_document_api.py
依赖更新：requirements.txt 添加 python-multipart>=0.0.9
- [x] 任务 5.1 - 文档解析与分块
实现文档解析与分块服务，补齐中文注释与单元测试，并按要求复核了规格文档。
parser.py：解析文本/Markdown/HTML/图片，支持 markitdown 解析 PDF/Office；图片无 OCR 则标记 ocr_skipped。
chunker.py：按 token 数分块、支持 overlap，并产出 chunk 元数据。
config.py：新增 RAG_CHUNK_SIZE、RAG_CHUNK_OVERLAP 配置。
requirements.txt：新增 markitdown>=0.0.1。
测试：test_document_parser.py、test_chunker.py。

实现向量写入与事务回滚：embedding.py（批量 embedding、维度校验、失败标记 failed 并记录 error_message，使用嵌套事务避免会话已有事务冲突）。
新增测试覆盖成功/失败路径：test_embedding_service.py。
- [x] 任务 5.2 - Embedding 写入与事务控制
- [x] 任务 6 - 语义检索与重排 API
新增搜索接口与服务层：embedding_service 提供可注入 embedder，retriever 基于 pgvector 余弦距离检索并对 SQLite 测试降级，reranker 提供可注入排序。
新增 Schema：search.py。
路由注册：main.py。
配置更新：config.py 增加 RAG_EMBEDDING_DIM。
新增测试：test_search_api.py。
- [x] 任务 7 - 健康探针与可观测性
新增 /health 与 /ready 探针，/ready 校验数据库连通与模型就绪；新增 /metrics 输出 Prometheus 指标（请求量/延迟、摄取计数、活跃 KB、chunk 总数），并接入请求与摄取计数采集。
新增测试：test_observability_api.py。
- [x] 任务 8 - 测试矩阵扩展
新增服务层单元测试（知识库状态机、清理任务执行、检索评分归一化与异常路径），补充检索 top_k 上限测试，并加入端到端流程、简化性能基准、并发与指标准确性测试，补齐解析失败路径与清理重试逻辑测试。
新增测试：test_end_to_end_flow.py、test_performance_smoke.py、test_concurrency.py。
- [x] 扩展 - SSE 流式对话接口
新增 `/chat/stream` SSE 接口，支持检索增强对话并输出 sources/delta/done 事件；新增配置 `RAG_LLM_*` 以接入模型 API；新增测试：test_chat_stream_api.py。

### 待开发
- [ ] 无
