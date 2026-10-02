# 规划智库 Backend Spec（MVP）

## 目标
面向 React/Vite 前端与 PRD V1.1，跑通：项目库、双层知识库、上传解析、联网搜索候选入库、双库问答、引用溯源、轻量文档生成。接口 JSON 默认使用前端 `types.ts` 的 camelCase 字段，同时 Pydantic 可接收 snake_case，便于测试和脚本调用。

## 技术栈
- FastAPI + SQLAlchemy Async
- SQLite 本地开发，后续可切 PostgreSQL/pgvector
- 文件存储：`storage/uploads`
- 当前 LLM/Search 为安全 stub，不真实外发 API Key

## 核心模型
- `Project`：项目库，字段：name、projectType、region、description。
- `Document`：资料元数据，区分 `knowledgeBase=project/general`；项目资料必须带 `projectId` 才会被当前项目检索。
- `DocumentChunk`：切片，保留 `section`、`clauseNumber`、`pageNumber`、`text`，引用只从 chunk 生成。
- `IngestionJob`：入库任务，状态 `pending/running/completed/failed`，步骤 `uploading/parsing/chunking/summarizing/vectorizing/ready`。
- `Conversation/ChatMessage/Citation`：会话、问答、引用卡片。
- `ProviderConfig`：大模型/搜索配置，密钥加密保存，响应只返回 masked key。

## API 约定
- `GET/POST /api/projects`：项目列表/创建。
- `GET/PATCH/DELETE /api/projects/{projectId}`：项目详情/更新/删除。
- `GET /api/documents?knowledgeBase=&projectId=`：资料列表。
- `POST /api/documents/upload`：multipart 上传，支持 `knowledgeBase/projectId/generateSummary`。
- `GET/PATCH/DELETE /api/documents/{docId}`：资料详情/更新/删除。
- `GET /api/documents/{docId}/chunks`：查看切片。
- `GET /api/documents/{docId}/ingestion-job`：查看最新解析任务。
- `POST /api/documents/{docId}/summarize`：按需摘要。
- `POST /api/search`：返回候选资料，不自动入库。
- `POST /api/search/candidates/{candidateId}/ingest`：用户确认后加入项目库或通用库。
- `GET/POST /api/projects/{projectId}/conversations`：会话列表/创建。
- `POST /api/conversations/{convId}/messages`：提问，默认双库检索。
- `POST /api/projects/{projectId}/drafts/generate`：轻量文档生成。
- `GET/POST /api/provider-configs`：配置保存与读取。

## 切片策略
MVP 使用结构感知切片：先按页，再按标题/条款/段落切分；默认 900 中文字符、150 字符重叠。保留章节、条款号和页码，优先保证引用可核查，而不是追求最小 chunk。后续接向量库时仍沿用该 chunk 结构。

## OCR 策略
默认 `OCR_MODE=off`。本地 OCR 只建议作为可选能力：图片可用 tesseract，扫描 PDF 还需要 poppler/pdf2image，部署复杂、CPU 占用高。生产建议优先接 OCR API 或独立 OCR worker，避免阻塞主服务。图片/扫描件若未配置 OCR，会给出提示并可重试。

## 检索与问答
当前使用本地关键词召回作为 pgvector 前的占位实现：
- `project`：只检索当前项目资料。
- `general`：只检索通用知识库。
- `both`：检索通用库 + 当前项目库，禁止跨项目泄漏。
回答由 LLM adapter 生成，但引用数据必须来自真实 chunk，模型不能自造引用。

## 下一步
1. 替换 `retrieval.py` 为 pgvector 相似度检索 + 关键词混合召回。
2. 将 `process_document` 移入 Celery/RQ/Arq 队列。
3. 增加真实 LLM、Embedding、Search Provider adapter。
4. OCR 放到独立 worker 或第三方 API。
5. 增加原文预览/页码跳转接口。
