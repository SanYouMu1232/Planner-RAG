"""Real pluggable web-search providers with explicit request/response diagnostics."""
from __future__ import annotations
from urllib.parse import urlparse
import httpx
from ..config import REQUEST_TIMEOUT_SECONDS

class SearchProviderError(RuntimeError): pass

def _normalise(name:str)->str:
    x=(name or "").lower().strip()
    if "博查" in name or "bocha" in x:return "bocha"
    if "tavily" in x:return "tavily"
    if "serper" in x:return "serper"
    if "serpapi" in x:return "serpapi"
    if "searx" in x:return "searxng"
    if "brave" in x:return "brave"
    return x

def _credibility(url:str,source:str="")->str:
    host=urlparse(url).hostname or ""
    if host.endswith(".gov.cn") or host.endswith(".gov"):return "政府官网"
    if any(x in host for x in ("std.samr.gov.cn","openstd.samr.gov.cn")):return "国家标准"
    if host.endswith(".edu.cn"):return "高校/研究机构"
    return source or "公开网页"

class SearchProvider:
    @staticmethod
    async def search(keyword:str,target:str="不限",region:str="",time_range:str="",provider_config:dict|None=None)->list[dict]:
        cfg=provider_config or {}; provider=_normalise(cfg.get("search_provider") or ""); key=(cfg.get("search_api_key") or "").strip(); endpoint=(cfg.get("search_base_url") or "").strip()
        if not provider or provider in {"none","暂不配置"}: raise SearchProviderError("未配置联网搜索服务。请在 API 配置中选择服务商并保存。")
        if provider!="searxng" and not key: raise SearchProviderError("联网搜索缺少 Search API Key。")
        query=" ".join(x for x in [keyword, target if target!="不限" else "", region, time_range] if x).strip()
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS,follow_redirects=True) as client:
            if provider=="bocha":
                r=await client.post(endpoint or "https://api.bochaai.com/v1/web-search",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"query":query,"count":10,"summary":True})
                data=_json_or_error(r,"博查")
                values=((data.get("data") or {}).get("webPages") or {}).get("value") or (data.get("data") or {}).get("value") or []
                return [_candidate(x.get("name") or x.get("title"),x.get("url"),x.get("summary") or x.get("snippet"),x.get("datePublished") or x.get("publishedDate"),"博查 AI Search") for x in values]
            if provider=="tavily":
                r=await client.post(endpoint or "https://api.tavily.com/search",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"query":query,"max_results":10,"search_depth":"advanced","include_answer":False,"include_raw_content":False})
                data=_json_or_error(r,"Tavily")
                return [_candidate(x.get("title"),x.get("url"),x.get("content"),x.get("published_date",""),"Tavily") for x in data.get("results",[])]
            if provider=="serper":
                r=await client.post(endpoint or "https://google.serper.dev/search",headers={"X-API-KEY":key,"Content-Type":"application/json"},json={"q":query,"num":10})
                data=_json_or_error(r,"Serper")
                return [_candidate(x.get("title"),x.get("link"),x.get("snippet"),x.get("date",""),"Serper") for x in data.get("organic",[])]
            if provider=="serpapi":
                r=await client.get(endpoint or "https://serpapi.com/search.json",params={"q":query,"api_key":key,"engine":"google","num":10})
                data=_json_or_error(r,"SerpApi")
                return [_candidate(x.get("title"),x.get("link"),x.get("snippet"),x.get("date",""),"SerpApi") for x in data.get("organic_results",[])]
            if provider=="searxng":
                if not endpoint: raise SearchProviderError("SearXNG 需要填写实例 Endpoint，例如 https://your-host/search。")
                r=await client.get(endpoint,params={"q":query,"format":"json","categories":"general"})
                data=_json_or_error(r,"SearXNG")
                return [_candidate(x.get("title"),x.get("url"),x.get("content"),x.get("publishedDate", ""),"SearXNG") for x in data.get("results",[])[:10]]
            if provider=="brave":
                r=await client.get(endpoint or "https://api.search.brave.com/res/v1/web/search",headers={"X-Subscription-Token":key,"Accept":"application/json"},params={"q":query,"count":10})
                data=_json_or_error(r,"Brave")
                return [_candidate(x.get("title"),x.get("url"),x.get("description"),x.get("age",""),"Brave") for x in (data.get("web") or {}).get("results",[])]
        raise SearchProviderError(f"未支持的搜索服务商：{cfg.get('search_provider')}")

def _json_or_error(resp:httpx.Response,name:str)->dict:
    try:data=resp.json()
    except Exception:data={"raw":resp.text[:500]}
    if resp.status_code>=400: raise SearchProviderError(f"{name} 调用失败（HTTP {resp.status_code}）：{data.get('message') or data.get('error') or data.get('detail') or str(data)[:400]}")
    return data

def _candidate(title,url,summary,publish_date,source):
    url=url or ""; return {"title":title or url or "未命名网页","source":source,"publish_date":publish_date or "","summary":summary or "","url":url,"credibility":_credibility(url,source),"reason":"来自用户配置的真实联网搜索结果，入库前请核对来源与时效。","category":"公开资料"}
