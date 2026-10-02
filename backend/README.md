# 规划智库后端

> 项目迭代：V11 · 需求基线：[PRD V1.1](../规划行业AI知识助手_PRD_v1.1.md)

后端采用 FastAPI + SQLite，支持项目库/通用库隔离、结构化资料解析、联网搜索入库、SSE 对话和引用溯源。

## 重点能力

- 百度智能云 **文档解析（PaddleOCR-VL）**：云端解析、表格、版面、阅读顺序；不使用本地 OCR。
- 本地结构化资料：DOCX、PDF、PPTX、XLSX、TXT/MD；旧 Office 格式支持 LibreOffice 转换提示。
- 网页正文及 HTML 表格抓取，并在用户明确确认后入库。
- 分片上传、取消上传、临时文件清理。
- 双层知识库检索、SQLite 追问记忆、SSE 逐字流式响应。
- Bocha、Tavily、Serper、SerpApi、SearXNG、Brave 联网搜索适配。

## 运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

测试与构建命令、验证结果统一记录在[根目录 README](../README.md#验证)。

运行时凭证通过 `/api/provider-configs` 保存。百度 OCR 凭证保存及云端调用需要风险确认；第三方密钥不应提交到版本库。
