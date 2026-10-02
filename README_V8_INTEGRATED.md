# 规划智库 · Planner V8 完整改造包

本包以用户提供的 `planner V8.zip` 为原始工程，按照《规划行业AI知识助手 PRD V1.1》及新增需求完成改造。前端为 React/Vite，后端为 FastAPI/SQLite；未携带用户资料、数据库、第三方密钥或 `node_modules`。

## 本次完成内容

| 需求 | 已实现内容 |
|---|---|
| 百度云 OCR | 接入百度智能云 **文档解析（PaddleOCR-VL）**：OAuth、异步提交、任务轮询、结构化 JSON/Markdown、表格 cells/matrix、版面坐标与阅读顺序；不配置本地 OCR。 |
| 云端风险确认 | 保存 OCR 配置和调用前均要求用户勾选“文件会传输到百度智能云”的风险确认；前端不会回显密钥。 |
| 表格识别 | DOCX、XLSX、PPTX 原生表格与 PDF 表格成为独立 `table` 内容块；聊天检索对表格查询提高召回权重；回答与原文抽屉均渲染 Markdown 表格。 |
| 多格式解析 | Word、PDF、PPT、Excel、TXT/MD、图片/扫描件与网页入库；旧 `.doc/.ppt/.xls` 可由 LibreOffice 转换，或选用云端文档解析。 |
| 版面与阅读顺序 | Word 使用 OOXML body 顺序；PPT 以幻灯片内上→下、左→右视觉位置；Excel 以工作表→行列顺序；PDF 按页内 y/x 坐标并保留 bbox；百度云结果保留 layout/span boxes。 |
| 模糊提问与追问 | 系统提示要求先陈述可验证理解与假设、仅在必要时提出一个关键澄清问题；SQLite 持久化最近 10 轮上下文。 |
| 联网查询 | 支持 Bocha、Tavily、Serper、SerpApi、SearXNG、Brave；按各服务实际鉴权头/HTTP 方法调用，并显示可诊断错误。搜索结果必须由用户主动入库后才参与问答。 |
| 上传中断 | 前端 `AbortController` + 后端分片上传会话取消和临时文件清理。 |
| 弹窗交互 | 所有配置、上传、抽屉和项目弹窗均只允许关闭按钮/取消按钮关闭，点击遮罩不退出。 |
| 长输出与排版 | 对话采用 SSE 流式输出，默认 `max_tokens=8192`，支持标题、列表、引用、Markdown 表格、工具状态与原文引用。 |

## 启动

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
npm install
npm run dev
```

打开 `http://localhost:5173`。如后端不在默认端口，请设置 `VITE_API_BASE_URL`，例如 `http://127.0.0.1:8000/api`。

## 使用顺序

1. 创建项目；上传资料到项目知识库，或上传政策/规范到通用知识库。
2. 在右上角“服务配置”中按需分别填写：大模型、联网搜索、百度云 OCR。
3. 对百度云 OCR，先阅读风险提示并明确勾选确认；上传扫描件或复杂版面文档时勾选“使用百度云端版面/表格解析”。
4. 在工作台直接提问。默认联检“当前项目知识库 + 通用知识库”；对话和文档生成会保留引用来源。
5. 先通过“搜索”查看公开资料，确认后选择加入当前项目库或通用库。

## 百度云 OCR 参数

- 服务名称：**文档解析（PaddleOCR-VL）**。
- 配置位置：服务配置 → 百度智能云：文档解析（PaddleOCR-VL）。
- 后端请求：OAuth token；文档解析任务提交、查询和结果下载。
- 默认请求能力：`analysis_chart=true`、`merge_tables=true`、`relevel_titles=true`、`return_span_boxes=true`。

## 已执行验证

```bash
cd backend
pytest -q
# 55 passed

cd ..
npm run build
# Vite production build passed
```

真实回归样本为用户提供的《色达县色塘片区国土空间总体规划（2021—2035年）》：

- DOCX 解析：521 个阅读顺序内容块、30 张结构化表格。
- 表格指标和人口预测文本均进入检索索引。
- 问题“到2035年常住人口是多少？”可命中“预计2035年片区常住人口31400人”及对应表格/上下文。

> 外部百度 OCR、联网搜索与大模型服务均需要用户自己的有效凭证。项目实现了真实协议调用、配置测试和错误诊断；本次打包测试未使用或伪造任何第三方密钥。
