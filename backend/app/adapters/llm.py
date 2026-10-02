"""OpenAI-compatible LLM adapter with long structured answers and conversation memory."""
from __future__ import annotations
import json, os, re
from collections.abc import AsyncIterator
from typing import Any
import httpx
from ..config import LLM_MAX_TOKENS, REQUEST_TIMEOUT_SECONDS
DEFAULT_MODELS={"deepseek":"deepseek-chat","openai":"gpt-4o-mini","openai compatible":"gpt-4o-mini","openai 兼容接口":"gpt-4o-mini","本地部署模型":"qwen2.5:14b"}
DEFAULT_BASE_URLS={"deepseek":"https://api.deepseek.com","openai":"https://api.openai.com/v1","openai compatible":"https://api.openai.com/v1","openai 兼容接口":"https://api.openai.com/v1","本地部署模型":"http://localhost:11434/v1"}
def _normalise_provider(p:str|None)->str:
    value=(p or "").strip(); low=value.lower()
    if not value:return "deepseek"
    if "deepseek" in low:return "deepseek"
    if "openai" in low and "兼容" not in value:return "openai"
    if "兼容" in value or "compatible" in low:return "openai compatible"
    if "local" in low or "本地" in value or "ollama" in low:return "本地部署模型"
    return value
def _runtime(config:dict[str,Any]|None=None)->dict[str,str]:
    c=config or {}; p=_normalise_provider(c.get("provider") or os.getenv("LLM_PROVIDER","DeepSeek")); return {"provider":p,"base_url":(c.get("base_url") or os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URLS.get(p,"")).strip().rstrip("/"),"model_name":(c.get("model_name") or os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(p,"deepseek-chat")).strip(),"api_key":(c.get("api_key") or os.getenv("LLM_API_KEY") or "").strip()}
def _chat_url(base:str)->str:
    base=base.rstrip("/")
    if base.endswith("/chat/completions"):return base
    if base.endswith("/v1"):return base+"/chat/completions"
    return base+"/v1/chat/completions"
def _citation_data(chunks:list[dict],limit:int=12)->list[dict]:
    result=[]
    for i,item in enumerate(chunks[:limit],1):result.append({"number":i,"document_id":item.get("document_id"),"chunk_id":item.get("chunk_id"),"document_name":item.get("file_name","未知文档"),"knowledge_base":item.get("knowledge_base","project"),"section":item.get("section") or ("表格" if item.get("chunk_type")=="table" else "正文"),"quote":(item.get("text") or "")[:420],"policy_status":item.get("policy_status","unknown")})
    return result
def _context(chunks:list[dict],max_chars:int=30000)->str:
    out=[];used=0
    for i,x in enumerate(chunks,1):
        text=(x.get("text") or "").strip()
        if not text:continue
        label="结构化表格" if x.get("chunk_type")=="table" else "正文"
        part=f"[证据 {i}｜{label}｜文件：{x.get('file_name','未知')}｜章节：{x.get('section') or '正文'}｜页/片：{x.get('page_start') or '-'}]\n{text}\n"
        if used+len(part)>max_chars:break
        out.append(part);used+=len(part)
    return "\n".join(out)
def _history(messages:list[dict])->str:
    items=[]
    for m in messages[-10:]:
        q=(m.get("question") or "").strip(); a=(m.get("answer") or "").strip()
        if q:items.append(f"用户：{q}\n助理：{a[:1800] if a else '（正在回答）'}")
    return "\n\n".join(items)

def _looks_like_greeting(question:str)->bool:
    q=re.sub(r"\s+", "", question.lower())
    return bool(q) and (q in {"你好","您好","hello","hi","在吗","你在吗","早上好","下午好","晚上好"} or q.endswith("好"))

def _simple_local_answer(question:str,history:list[dict]|None=None)->str:
    q=question.strip()
    if _looks_like_greeting(q):
        return "我在，可以正常交流。你可以直接问资料里的内容，也可以让我帮你分析、改写、拟提纲或排查系统问题。"
    if any(x in q for x in ("谢谢","感谢","辛苦")):
        return "不客气。你继续把问题或现象发给我，我会按能定位、能修改、能验证的方式继续处理。"
    if any(x in q for x in ("你能做什么","有什么功能","怎么用")):
        return "我可以做三类事情：\n1. 围绕项目知识库回答，并给出引用依据。\n2. 在知识库没有命中时，按常规对话继续解释、分析或帮你梳理思路。\n3. 协助检查上传、联网搜索、切块、召回、摘要和页面交互等功能问题。\n当前没有配置可用大模型时，复杂开放问题只能给出基础处理建议；配置模型后可以输出更完整的分析。"
    return "当前知识库没有检索到可引用依据。\n\n我仍可以按常规对话先帮你处理：请补充你希望我分析的背景、目标或截图；如果这是资料问答，建议上传或入库相关原文后再追问，这样我能给出可核验引用。\n\n当前未配置可用大模型服务，因此复杂开放问题暂时无法生成完整长答案；请在 API 配置中保存可用模型后再试。"

def _fallback(question:str,chunks:list[dict],history:list[dict]|None=None)->str:
    if not chunks:return _simple_local_answer(question,history)
    lines=["已检索到可核验依据","","当前未配置可用的大模型服务。下面先列出与问题最相关的正文或表格依据；配置模型后系统会基于这些证据生成完整分析。",f"问题：{question}",""]
    for i,x in enumerate(chunks[:8],1): lines+= [f"[{i}] {x.get('file_name','未知文档')} · {x.get('section') or ('表格' if x.get('chunk_type')=='table' else '正文')}",x.get("text","")[:1200],""]
    return "\n".join(lines)
SYSTEM="""你是“规划智库”的资深国土空间规划师与资料核验助手。
输出格式要求：不要使用大量 Markdown 标记，不要用 # 号标题，不要用 ** 加粗。用清晰的中文小标题和自然段组织，例如“结论：”“依据：”“分析：”“建议：”。需要列表时用 1. 2. 3.，需要对比时可以使用 Markdown 表格。引用使用 [证据 n]，n 必须存在。
资料问答规则：凡涉及项目文件、政策条款、数值、表格、来源核验的问题，优先依据给出的【证据】回答，不要编造证据外的具体文件内容；如证据不足，要说明“当前知识库未找到明确依据”，再给出可执行的补充检索或上传建议。
常规对话规则：如果用户是在闲聊、写作、解释概念、提需求、让你分析系统问题，或【证据】为空，不能直接拒绝。应先说明知识库没有命中或没有可引用依据，然后按通用能力继续回答；但不得把通用判断伪装成知识库结论。
面对模糊问题，先写出最合理且可验证的理解与假设；只有当不同理解会造成明显不同结论时，在结尾提出一个最关键的澄清问题。对追问必须结合对话历史，不得重复询问用户已经提供的信息。"""
class LLMProvider:
 @staticmethod
 async def stream_chat(question:str,knowledge_source:str,chunks:list[dict]|None=None,provider_config:dict|None=None,history:list[dict]|None=None)->AsyncIterator[str]:
    ready=chunks or [];cfg=_runtime(provider_config)
    if not cfg["api_key"]:
        yield _fallback(question,ready,history);return
    source={"project":"当前项目知识库","general":"通用知识库","both":"通用知识库 + 当前项目知识库"}.get(knowledge_source,"知识库")
    evidence_text=_context(ready) if ready else "（本轮没有检索到可引用的知识库证据。可以进行常规对话，但涉及项目资料的结论必须说明没有知识库依据。）"
    user=f"知识范围：{source}\n\n【对话历史】\n{_history(history or []) or '（无）'}\n\n【证据】\n{evidence_text}\n\n【本轮问题】\n{question}\n\n请按清晰自然的中文结构输出，少用符号，不要堆叠 #、* 等 Markdown 标记。"
    payload={"model":cfg["model_name"],"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":user}],"temperature":0.2,"max_tokens":LLM_MAX_TOKENS,"stream":True}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS,read=180),follow_redirects=True) as client:
            async with client.stream("POST",_chat_url(cfg["base_url"]),headers={"Authorization":f"Bearer {cfg['api_key']}","Content-Type":"application/json","Accept":"text/event-stream"},json=payload) as r:
                if r.status_code>=400:
                    body=await r.aread();yield f"\n\n模型调用失败（HTTP {r.status_code}）：{body.decode('utf-8','replace')[:500]}";return
                received=False
                async for line in r.aiter_lines():
                    if not line.startswith("data:"):continue
                    raw=line[5:].strip()
                    if raw=="[DONE]":break
                    try:delta=json.loads(raw)["choices"][0].get("delta",{}).get("content","")
                    except Exception:delta=""
                    if delta:received=True;yield delta
                if not received:yield "\n\n模型未返回可显示内容。请检查模型名称、权限或流式协议。"
    except Exception as exc:yield f"\n\n模型调用失败：{exc}"
 @staticmethod
 async def chat(question:str,knowledge_source:str="both",chunks:list[dict]|None=None,provider_config:dict|None=None,history:list[dict]|None=None)->tuple[str,list[dict]]:
    ready=chunks or [];parts=[]
    async for d in LLMProvider.stream_chat(question,knowledge_source,ready,provider_config,history):parts.append(d)
    return "".join(parts),_citation_data(ready)
 @staticmethod
 async def summarize(text:str,file_name:str="",provider_config:dict|None=None)->str:
    clean=" ".join((text or "").split())
    if not clean:return f"《{file_name}》暂未提取到有效正文，建议检查扫描件或云端 OCR 配置。"
    cfg=_runtime(provider_config)
    if not cfg["api_key"]:return f"《{file_name}》已完成结构化解析。正文预览：{clean[:260]}…"
    payload={"model":cfg["model_name"],"messages":[{"role":"system","content":"你是规划资料整理助手。只根据资料生成150-250字结构化摘要，不编造。输出用自然中文小标题，不要堆叠 #、* 符号。"},{"role":"user","content":f"文件名：{file_name}\n资料：{clean[:14000]}"}],"temperature":0.2,"max_tokens":700}
    try:
      async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
       r=await client.post(_chat_url(cfg["base_url"]),headers={"Authorization":f"Bearer {cfg['api_key']}","Content-Type":"application/json"},json=payload);r.raise_for_status();return r.json().get("choices",[{}])[0].get("message",{}).get("content","").strip() or f"《{file_name}》已完成解析。"
    except Exception as exc:return f"《{file_name}》已完成解析，但摘要模型调用失败：{exc}"
 @staticmethod
 async def test_connection(provider_config:dict[str,Any])->tuple[bool,str]:
    cfg=_runtime(provider_config)
    if not cfg["api_key"]:return False,"请先填写大模型 API Key。"
    if not cfg["base_url"] or not cfg["model_name"]:return False,"请填写 Base URL 与模型名称。"
    payload={"model":cfg["model_name"],"messages":[{"role":"user","content":"仅回复：连接测试成功"}],"temperature":0,"max_tokens":30}
    try:
      async with httpx.AsyncClient(timeout=30) as client:
       r=await client.post(_chat_url(cfg["base_url"]),headers={"Authorization":f"Bearer {cfg['api_key']}","Content-Type":"application/json"},json=payload);r.raise_for_status()
      return True,f"连接测试成功：{cfg['provider']} / {cfg['model_name']} 已真实返回响应。"
    except httpx.HTTPStatusError as exc:return False,f"连接测试失败：HTTP {exc.response.status_code}，{exc.response.text[:300]}"
    except Exception as exc:return False,f"连接测试失败：{exc}"
