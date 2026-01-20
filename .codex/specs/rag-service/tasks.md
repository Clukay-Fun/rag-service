# Implementation Plan

- [x] 1. FastAPI 应用骨架与配置加载
  - 搭建 `app/main.py`、`app/config.py`，统一 `RAG_` 前缀环境变量，注入 pg/pgvector 连接。
  - 中间件生成 `request_id` 写入响应头 `X-Request-ID` 与结构化日志；实现统一错误响应格式与资源校验顺序（存在性→可用性→权限）。
  - _Requirements: Technical Conventions (错误格式/校验顺序/环境变量), Requirement 5 AC1-3_

- [x] 2. 数据模型与迁移（knowledge_bases/documents/document_chunks/cleanup_tasks）
  - 定义表结构、状态枚举、外键/索引（pgvector HNSW `vector_cosine_ops`），确保向量维度 1024；迁移脚本创建 HNSW 索引。
  - _Requirements: Requirement 1 AC1-11, Requirement 2 AC1-12, Requirement 3 AC1-7, Requirement 4 AC1-4_

- [x] 3. 知识库管理服务与 API
  - 实现创建/更新/删除/列表逻辑（名称唯一、状态机、deleted 后拒绝修改）；DELETE 返回 `cleanup_task_id` 并入队清理任务；分页/过滤。
  - _Requirements: Requirement 1 AC1-11, Requirement 5 AC2_

- [x] 4. 清理任务执行器与任务查询/重试接口
  - 后台 worker 级联删除文档/分块/向量，记录 progress（processed/total/percentage）、error_message；失败指数退避重试、重试接口校验可重试状态。
  - _Requirements: Requirement 1 AC6-11, Requirement 5 AC2-3_

- [ ] 5. 文档上传入口与摄取状态查询
  - `POST /knowledge_bases/{kb_id}/documents`：校验 KB 可用，检查大小/媒体类型，返回 202 与 `document_id`、`status=processing`；`GET /documents/{id}` & 列表支持状态过滤、410 语义。
  - _Requirements: Requirement 2 AC1-12, Requirement 5 AC2-4_

- [ ] 5.1 文档解析与分块
  - 后台任务用 markitdown+OCR 解析 PDF/Word/Excel/PPT/TXT/Markdown/HTML/图片，保留结构；按 BGE-M3 tokenizer `chunk_size`/`overlap` 切分并记录元数据（文件名、页码/序号、ocr_skipped）。
  - _Requirements: Requirement 2 AC1-7, Technical Conventions (分块/向量化)_

- [ ] 5.2 Embedding 写入与事务控制
  - 使用 BGE-M3 生成 L2 归一化向量，事务性写入 chunks+vectors；任意分块失败则回滚、标记文档 `failed`+error_message，成功则置 `completed` 并记录 chunk_count。
  - _Requirements: Requirement 2 AC4-9, Requirement 5 AC3_

- [ ] 6. 语义检索与 rerank API
  - `POST /search`：校验 KB 状态 enabled，仅检索 `completed` 文档分块；query embedding→pgvector cosine 取 min(top_k*3, RAG_MAX_RERANK_CANDIDATES) 候选→bge-reranker sigmoid 归一→返回 chunk_text/score/document_id/filename/chunk_index。
  - _Requirements: Requirement 3 AC1-7, Technical Conventions (相关性归一)_

- [ ] 7. 健康探针与可观测性
  - 实现 `/health`（存活）与 `/ready`（就绪，检查 DB/模型加载），依赖未就绪返回 503；Prometheus `/metrics` 输出请求量/延迟、摄取成功失败、活跃 KB、chunk 总量指标；结构化日志覆盖异常堆栈。
  - _Requirements: Requirement 4 AC1-4, Requirement 5 AC1-5_

- [ ] 8. 测试矩阵
  - 单元：KB 服务状态机、分块策略、评分归一化、清理重试、配置边界（top_k/文件大小）。
  - 集成/契约：FastAPI TestClient 覆盖 CRUD/摄取/检索 happy-path 与 4xx/5xx、错误 schema；运行小型 pgvector 容器演练上传→检索全链路（可 mock 模型以控资源）。
  - _Requirements: 全部（验证功能/错误/性能基线）_
