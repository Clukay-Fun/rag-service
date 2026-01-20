# Requirements Document

## Introduction

本规范定义了一个独立的 RAG 检索服务。服务以 FastAPI 为入口，使用 PostgreSQL + pgvector 存储向量，采用 BGE-M3 作为 embedding 模型、BAAI/bge-reranker-v2-m3 进行 rerank。目标是为其他 AI 应用（如招投标助手）提供可管理的知识库、文档摄取、语义检索与重排序能力,并满足低延迟、可观测、稳健的交付要求。

使用中文回答，使用中文注释。

## Technical Conventions

### 错误响应格式

所有 API 错误响应 SHALL 遵循以下统一 schema：

```json
{
  "error": {
    "code": "KNOWLEDGE_BASE_NOT_FOUND",
    "message": "Knowledge base with id 'xxx' not found",
    "request_id": "uuid-v4",
    "details": [
      {
        "field": "knowledge_base_id",
        "code": "NOT_FOUND",
        "message": "Resource does not exist"
      }
    ]
  }
}
```

### 资源校验顺序约定

所有需要引用资源（如 knowledge_base_id、document_id、task_id）的接口 SHALL 按以下顺序进行校验，以避免实现差异：

1. **存在性校验**：先检查资源是否存在；IF 不存在 THEN 返回 404。
2. **可用性校验**：资源存在但处于不可用状态（如 disabled/deleted）THEN 返回 403（或规范中定义的其他语义化状态码，如 410）。
3. **权限校验**：在存在且可用前提下，进行权限判定；IF 无权限 THEN 返回 401/403。

### 分块与向量化约定

1. **Tokenizer**：分块时 SHALL 使用 BGE-M3 模型对应的 tokenizer（基于 XLM-RoBERTa）计算 token 数量。
2. **向量归一化**：embedding 向量在存入 pgvector 前 SHALL 进行 L2 归一化，以确保余弦相似度计算的正确性。
3. **索引类型**：pgvector SHALL 使用 HNSW 索引，operator class 为 `vector_cosine_ops`。
4. **HNSW 参数默认值**：pgvector SHALL 使用 HNSW 索引参数 `m=16`、`ef_construction=64`；查询时 `ef_search` 默认 40，可通过环境变量 `RAG_HNSW_EF_SEARCH` 调整。

### 相关性分数归一化

reranker 输出的原始分数 SHALL 通过 sigmoid 函数归一化至 0-1 范围：`score = 1 / (1 + exp(-raw_score))`。

### 环境变量命名约定

所有可配置项 SHALL 使用 `RAG_` 前缀，采用全大写下划线分隔风格，例如：

* `RAG_MAX_DOCUMENT_SIZE`
* `RAG_MAX_TOP_K`
* `RAG_MAX_RERANK_CANDIDATES`
* `RAG_HNSW_EF_SEARCH`

### 性能测试环境假设

Requirement 4 中的性能指标基于以下部署假设：

* GPU：单卡 NVIDIA T4 或同等算力（16GB 显存）
* 模型加载：BGE-M3 与 reranker 模型常驻 GPU 显存
* 数据库：PostgreSQL 15+ with pgvector 0.5+，SSD 存储，连接池 ≥20
* 服务实例：单实例 4 worker 进程

## Requirements

### Requirement 1 — 知识库管理 API

**User Story:** As an AI 应用开发者, I want to 管理、查询、删除知识库 via HTTP API, so that I can 为不同应用隔离数据域并保持资源可控。

#### Acceptance Criteria

1. WHEN 客户端以唯一名称创建知识库 THEN 系统 SHALL 持久化知识库并返回包含 id、name、status、created_at 的 201 响应。
2. IF 客户端创建知识库时使用已存在的名称（全局唯一，限当前服务实例范围） THEN 系统 SHALL 返回 409 Conflict 并提示名称冲突。
3. WHEN 创建知识库 THEN 系统 SHALL 默认设置 status 为 `enabled`；知识库状态枚举包括 `enabled`、`disabled`、`deleted`（内部状态，标记待清理的知识库）。
4. WHEN 客户端调用 PATCH /knowledge_bases/{id} 更新知识库 THEN 系统 SHALL 支持更新 name、description、status 字段；IF 更新 status 为 `disabled` THEN 该知识库 SHALL 不可用于检索；IF 当前 status 为 `deleted` THEN 系统 SHALL 拒绝任何 status 变更并返回 409 Conflict（已删除的知识库不可恢复或修改），错误码为 `KNOWLEDGE_BASE_DELETED`。
5. IF 客户端更新或删除不存在的知识库 id THEN 系统 SHALL 返回 404 并提供结构化错误码与消息。
6. WHEN 删除知识库 THEN 系统 SHALL 立即将知识库标记为 `deleted` 状态并返回 202 Accepted，响应体包含 cleanup_task_id 用于后续任务状态查询；后台任务 SHALL 异步级联清理其关联的文档、分块与向量记录。
7. IF 删除后台任务失败 THEN 系统 SHALL 记录失败日志并自动重试（最多 3 次，指数退避间隔 1/2/4 分钟）；IF 3 次重试均失败 THEN 任务状态 SHALL 更新为 `failed`；知识库在 `deleted` 状态下 SHALL 不可被检索或用于文档上传，但仍可通过管理 API（列表/详情）查询以供运维审计。
8. WHEN 客户端调用 GET /cleanup_tasks/{task_id} THEN 系统 SHALL 返回清理任务状态，包括 task_id、knowledge_base_id、status（`pending`/`running`/`completed`/`failed`）、progress、error_message、created_at、updated_at；其中 progress SHALL 使用如下 schema：

   ```json
   "progress": {
     "processed": 0,
     "total": null,
     "percentage": null
   }
   ```

   * `processed`：已清理资源数（total 为 null 时仍可递增）
   * `total`：总资源数；为 null 表示无法预估，客户端应显示 spinner 而非百分比进度条
   * `percentage`：仅当 total 非 null 时计算，否则为 null
   * 当 status=`pending` 时 progress.processed SHALL 为 0
   * 当 status=`completed` 时 progress.total SHALL 为非 null 且 progress.processed == progress.total，percentage==1.0
9. IF 客户端调用 GET /cleanup_tasks/{task_id} 且 task_id 不存在 THEN 系统 SHALL 返回 404 Not Found，错误码为 `CLEANUP_TASK_NOT_FOUND`。
10. WHEN 客户端调用 POST /cleanup_tasks/{task_id}/retry THEN 系统 SHALL 仅允许对 status 为 `failed` 的任务执行重试；IF 任务可重试 THEN 系统 SHALL 将任务状态重置为 `pending` 并重新启动清理；IF 任务不存在 THEN 返回 404；IF 任务状态非 `failed` THEN 返回 409 Conflict，错误码为 `CLEANUP_TASK_NOT_RETRYABLE`。
11. WHEN 列出知识库 THEN 系统 SHALL 支持分页（page、page_size）、按名称模糊过滤（name_contains）、按状态过滤（status，可包含 `deleted`），并返回 items 列表与 total 总数。

### Requirement 2 — 文档上传与摄取

**User Story:** As a 知识库维护者, I want to 上传常见文档格式并完成向量化摄取, so that 内容能进入向量库以支持检索。

#### Acceptance Criteria

1. WHEN 客户端调用 POST /knowledge_bases/{kb_id}/documents 上传文档 THEN 系统 SHALL 先校验目标知识库存在性；IF 知识库不存在 THEN 返回 404 Not Found（`KNOWLEDGE_BASE_NOT_FOUND`）；IF 知识库 status 为 `disabled` 或 `deleted` THEN 返回 403 Forbidden（`KNOWLEDGE_BASE_UNAVAILABLE`）；校验通过后系统 SHALL 返回 202 Accepted 及 document_id、status 为 `processing`；文档状态枚举包括 `processing`、`completed`、`failed`、`deleted`（删除墓碑状态，仅用于区分已删除与从未存在）。
2. WHEN 系统接收文档 THEN 系统 SHALL 使用 markitdown 库将文档转换为 Markdown 格式，保留标题、列表、表格等结构信息；支持的格式包括 PDF、Word（.docx）、Excel（.xlsx）、PPT（.pptx）、TXT、Markdown、HTML 及常见图片格式（.png、.jpg、.jpeg）。
3. WHEN 处理图片文件或文档中的嵌入图片 THEN 系统 SHALL 调用 OCR 能力提取文字内容；IF OCR 依赖不可用 THEN 系统 SHALL 跳过图片内容并在文档元数据中标记 `ocr_skipped: true`。
4. IF 文档格式不被支持 THEN 系统 SHALL 返回 415 Unsupported Media Type 并在响应中列出支持的格式。
5. IF 上传文档超过可配置大小上限（默认 50MB，可通过 `RAG_MAX_DOCUMENT_SIZE` 环境变量配置） THEN 系统 SHALL 拒绝并返回 413 Payload Too Large。
6. WHEN Markdown 转换成功 THEN 系统 SHALL 使用 BGE-M3 tokenizer 按可配置 chunk_size（默认 512 tokens）与 overlap（默认 64 tokens）切分文本，并记录来源文件名与 chunk 序号。
7. WHEN 分块完成 THEN 系统 SHALL 使用 BGE-M3 生成 embedding 并进行 L2 归一化后存入 pgvector；向量记录包含 knowledge_base_id、document_id、chunk_index、chunk_text、metadata（文件名、创建时间）。
8. WHEN 所有分块 embedding 成功写入 THEN 系统 SHALL 在单个数据库事务中提交，并将文档状态更新为 `completed`。
9. IF markitdown 转换失败或任一分块 embedding 失败 THEN 系统 SHALL 回滚已写入的向量记录、将文档状态更新为 `failed`、记录 error_message，确保不对外提供部分可检索结果。
10. WHEN 客户端调用 GET /documents/{id} THEN 系统 SHALL 返回文档详情，包括 id、knowledge_base_id、filename、status（`processing`/`completed`/`failed`/`deleted`）、error_message、chunk_count、created_at、updated_at。
11. WHEN 客户端调用 GET /knowledge_bases/{kb_id}/documents THEN 系统 SHALL 返回该知识库下的文档列表，支持分页与按 status 过滤。
12. WHEN 客户端调用 DELETE /documents/{id} THEN 系统 SHALL 删除文档记录并级联删除其所有分块与向量记录，返回 204 No Content；IF 文档 id 从未存在 THEN 系统 SHALL 返回 404 Not Found（`DOCUMENT_NOT_FOUND`）；IF 文档已被删除（status=`deleted`） THEN 系统 SHALL 返回 410 Gone（`DOCUMENT_DELETED`）。

### Requirement 3 — 语义检索与重排序

**User Story:** As a 下游 AI 服务调用方, I want to 以查询词检索指定知识库并得到相关片段, so that 我能生成更准确的回答。

#### Acceptance Criteria

1. WHEN 客户端提交 POST /search 包含 query、knowledge_base_id 与可选 top_k THEN 系统 SHALL 使用 BGE-M3 对 query 向量化并进行 L2 归一化，默认 top_k=5，上限可配置（默认最大 20，通过 `RAG_MAX_TOP_K` 环境变量配置）。
2. WHEN 执行向量检索 THEN 系统 SHALL 仅在对应 knowledge_base_id 且 status 为 `enabled` 的知识库范围内，从 status 为 `completed` 的文档关联的 chunk 中查询，使用 pgvector 的 `<=>` 算子（cosine distance）并按距离升序取前 min(top_k * 3, RAG_MAX_RERANK_CANDIDATES) 条候选供 rerank 使用（`RAG_MAX_RERANK_CANDIDATES` 默认 100，可通过环境变量配置）。
3. WHEN 获取候选 THEN 系统 SHALL 使用 BAAI/bge-reranker-v2-m3 对 query 与候选 chunk 进行 rerank，将原始分数通过 sigmoid 归一化至 0-1，并按分数降序返回前 top_k 条结果。
4. WHEN 返回检索结果 THEN 系统 SHALL 返回数组，每项包含：chunk_text、score（0-1 归一化）、document_id、filename、chunk_index。
5. IF knowledge_base_id 不存在 THEN 系统 SHALL 返回 404 Not Found。
6. IF knowledge_base_id 对应的知识库 status 为 `disabled` 或 `deleted` THEN 系统 SHALL 返回 403 Forbidden 并提示知识库不可用，错误码为 `KNOWLEDGE_BASE_UNAVAILABLE`，不暴露内部存储信息。
7. IF 知识库内无任何已完成摄取的文档（status 为 `completed`） THEN 系统 SHALL 返回空数组而非错误。

### Requirement 4 — 性能与可扩展性

**User Story:** As a 平台拥有者, I want to 服务在并发与规模下保持低延迟, so that 用户体验稳定且可扩展。

#### Acceptance Criteria

1. WHEN 在单知识库 ≤100k 个 chunk、top_k=5 的场景下执行检索 THEN 系统 SHALL 在暖机状态（模型已加载至 GPU 显存、数据库连接池已建立、HNSW 索引已加载、首次请求已完成）下提供 p95 ≤300ms 的响应（含 embedding、pgvector 查询与 rerank）。
2. WHEN 并发请求达到 20 RPS（其中 90% 为检索请求、10% 为文档上传请求，检索请求 top_k=5，目标知识库 chunk 数量 ≤50k）THEN 系统 SHALL 保持错误率 <1%，且 p99 延迟 ≤1s。
3. IF 后台摄取任务运行中（≤3 个并发文档处理） THEN 系统 SHALL 确保检索 p95 延迟相较空闲基线劣化不超过 20%。
4. WHEN 服务启动 THEN 系统 SHALL 暴露 GET /health（存活检查，仅检查进程存活）与 GET /ready（就绪检查，验证数据库连接可用且模型加载完成）端点；IF /ready 检查未通过 THEN 系统 SHALL 返回 503 Service Unavailable，配合容器编排系统（如 Kubernetes readiness probe）实现流量路由控制。

### Requirement 5 — 可观测性与错误处理

**User Story:** As an 运维人员, I want to 获得清晰的错误与监控指标, so that 我能快速定位问题并保障服务 SLA。

#### Acceptance Criteria

1. WHEN 任一 API 请求到达 THEN 系统 SHALL 生成唯一 request_id（UUID v4）并在响应头 X-Request-ID 中返回。
2. WHEN API 校验失败（如参数缺失、格式错误、业务规则违反） THEN 系统 SHALL 返回 4xx 状态码及符合 Technical Conventions 定义的错误响应格式，包含 code、message、request_id、details（字段级错误列表）。
3. WHEN 内部异常发生 THEN 系统 SHALL 返回 500 Internal Server Error，响应体仅包含 code（INTERNAL_ERROR）、message（通用提示）、request_id，不泄露堆栈或敏感信息；同时以结构化日志（JSON 格式）记录完整堆栈、request_id、请求参数。
4. WHEN 文档摄取流程任一阶段失败 THEN 系统 SHALL 在文档记录中更新 status 为 `failed` 并填充 error_message；客户端可通过 GET /documents/{id} 查询摄取状态与失败原因。
5. WHEN 监控开启（默认开启） THEN 系统 SHALL 通过 GET /metrics 端点输出 Prometheus 格式指标（使用 Histogram 类型，支持通过 PromQL 计算分位数），包括：

   * `http_requests_total{method, endpoint, status}` — 请求计数（Counter）
   * `http_request_duration_seconds{method, endpoint}` — 延迟分布（Histogram，buckets 覆盖 0.01s 至 10s）
   * `document_ingestion_total{status}` — 摄取成功/失败计数（Counter）
   * `knowledge_bases_active` — 活跃（enabled）知识库数量（Gauge）
   * `chunks_total` — 向量库中总 chunk 数量（Gauge）

## Appendix A — 交付规范

本节定义开发交付物的要求，非系统功能性需求。

### 交付要求

1. 代码必须符合上述功能规范，每次交付须提供完整可运行的代码。
2. 每个模块须附带对应的单元测试与集成测试代码，测试覆盖率目标 ≥80%。
3. 交付时须说明 README.md 需要更新的内容，包括：安装步骤、环境变量配置说明、API 文档链接、本地开发与运行示例。

## Appendix B — 标准错误码表

| HTTP Status | Error Code                   | 说明              |
| ----------- | ---------------------------- | --------------- |
| 400         | VALIDATION_ERROR             | 请求参数校验失败        |
| 404         | KNOWLEDGE_BASE_NOT_FOUND     | 知识库不存在          |
| 404         | DOCUMENT_NOT_FOUND           | 文档不存在（从未存在）     |
| 404         | CLEANUP_TASK_NOT_FOUND       | 清理任务不存在         |
| 403         | KNOWLEDGE_BASE_UNAVAILABLE   | 知识库不可用（已禁用或已删除） |
| 409         | KNOWLEDGE_BASE_NAME_CONFLICT | 知识库名称冲突         |
| 409         | KNOWLEDGE_BASE_DELETED       | 知识库已删除，不可恢复或修改  |
| 409         | CLEANUP_TASK_NOT_RETRYABLE   | 清理任务当前状态不可重试    |
| 410         | DOCUMENT_DELETED             | 文档已删除（资源已不存在）   |
| 413         | PAYLOAD_TOO_LARGE            | 上传文件超过大小限制      |
| 415         | UNSUPPORTED_MEDIA_TYPE       | 不支持的文件格式        |
| 500         | INTERNAL_ERROR               | 内部服务错误          |
| 503         | SERVICE_UNAVAILABLE          | 服务未就绪           |
