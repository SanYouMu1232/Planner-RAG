# Codex 后端工作流程

1. 先运行测试：`python -m pytest -q`，不要在失败状态继续加功能。
2. 新功能优先保持接口字段与前端 `src/types.ts` 对齐：响应 camelCase，请求兼容 camelCase/snake_case。
3. 资料入库必须走：保存文件 -> 创建 Document -> 创建 IngestionJob -> 提取文本 -> chunk -> 摘要可选 -> embedding 占位/向量化 -> ready。
4. 搜索结果只能作为 Candidate，用户点击入库后才创建 Document。
5. 问答必须先检索 chunk，再生成回答；Citation 只能引用已有 chunk。
6. 项目知识库必须按 projectId 隔离；both 只能查通用库 + 当前项目库。
7. API Key 不允许回显明文；只返回 masked key。
8. 增加真实 OCR/LLM/Search 时必须走 adapter，不要把服务商逻辑写进 router。
9. 每次改动补测试，至少覆盖成功路径、404/422、项目隔离、引用字段。
