# 招投标助手系统开发说明（UTF-8）

## 一、项目概述
- 背景：基于 LlamaIndex 的“编排器-技能”架构，实现可扩展的智能助手。
- 目标与指标：首字 <500ms；简单查询 <1.5s；复杂分析 <5s；可用性 >99.5%。
- 模型配置：推理 DeepSeek-R1-Distill-Qwen-7B；任务 Qwen3-8B；对话 internlm2_5-7b-chat；向量 BAAI/bge-m3(1024)；Rerank BAAI/bge-reranker-v2-m3；视觉 GLM-4.1V-9B-Thinking。

## 二、里程碑与迭代
- M1 核心骨架：Skill 基类/注册、规则路由、对话技能、/chat 接入。
- M2 检索能力：向量+关键词混合检索，tsvector+GIN，ILIKE+pg_trgm，可选 rerank，缓存（当前未启用）。
- M3 分析能力：LLM Pool、合同/风险等分析技能、SSE 流式、LLM 分类兜底。
- M4 提取能力：合同/业绩/资质提取、文档解析、报告技能。

## 三、进度完成情况
迭代 1
- [x] Skill 基础设施/注册中心/数据模型
- [x] 对话类技能：greeting/help/chitchat
- [x] 规则路由与 /chat 接入
- [ ] 单测覆盖率 > 80%

迭代 2
- [x] 混合检索：向量 + 关键词 + 可选 rerank
- [x] 业绩/合同：tsvector + GIN 索引
- [x] 企业/律师：ILIKE + pg_trgm 索引
- [x] 检索测试用例（混合与关键词）
- [ ] Redis 缓存（当前不可用）
- [ ] 检索类 Skills（主系统侧待接入）

迭代 3
- [ ] LLM Pool 与分析类 Skills
- [ ] /chat/stream(SSE) 与 LLM 分类兜底

迭代 4
- [ ] 提取类 Skills 与文档解析服务
- [ ] 报告类 Skills


迭代 56
- [ ] 多 Skill 编排器
- [ ] 监控与链路追踪

## 四、快速使用
- 启动：`uvicorn app.main:app --reload --port 8001`
- 聊天：`POST /api/v1/chat`，字段 `message`
- 检索：`POST /api/v1/search/`，字段 `query/collection/top_k/use_rerank`
- 索引：`POST /api/v1/search/index`，批量写入文档
- 合同样本入库（已完成）：`scripts/ingest_contracts.py --folder E:\documents\业绩 --collection contracts`

## 五、测试
- 运行全部测试：`pytest -q`
- 仅检索：`pytest tests/test_retriever.py -q`
- 仅路由：`pytest tests/test_router.py -q`
- 端到端（聊天+检索）：`pytest tests/test_api_e2e.py -q`
