RAG 服务构建总结
已完成的文件
文件	说明
config.py	数据库、API、模型配置
database.py	数据库连接、初始化
models.py	Document 向量文档模型
embedding.py	向量生成（单条/批量）
retriever.py	向量检索、Rerank、混合搜索
search.py	搜索 API（检索/索引/删除）
main.py	FastAPI 入口
__init__.py x4	包初始化文件
requirements.txt	Python 依赖
.env	环境变量
API 接口
方法	路径	说明
POST	/api/v1/search/	语义搜索
POST	/api/v1/search/index	文档索引
DELETE	/api/v1/search/{collection}	删除数据集
GET	/api/v1/search/collections	列出数据集
GET	/health	健康检查
启动命令

cd E:\.Program\Python\rag-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
需要修复的问题
models.py 中的 metadata 字段需要改名为 doc_metadata（SQLAlchemy 保留字冲突）

下一步
修复 metadata 字段命名问题
启动 RAG 服务测试
在投标助手中创建 RAG 客户端调用服务

Update Todos

构建 RAG 服务 - config.py 配置

构建 RAG 服务 - database.py 数据库连接

构建 RAG 服务 - models.py 数据模型

构建 RAG 服务 - embedding.py 向量生成

构建 RAG 服务 - retriever.py 检索逻辑

构建 RAG 服务 - search.py API 接口

构建 RAG 服务 - main.py 入口

创建 RAG 服务 - __init__.py 文件

创建 RAG 服务 - requirements.txt

创建 RAG 服务 - .env 配置