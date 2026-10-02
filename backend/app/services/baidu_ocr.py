"""Baidu Cloud OCR adapter for 文档解析（PaddleOCR-VL）.

No local OCR dependency is used. The service is asynchronous: submit a document,
poll task status, then normalize layouts/tables into the app's structured blocks.
"""
from __future__ import annotations
import asyncio, base64, time
from pathlib import Path
from typing import Any
import httpx
from .text_extractor import ExtractedText, LayoutBlock, PageContent
from ..config import BAIDU_OCR_TOKEN_URL, BAIDU_OCR_TASK_URL, BAIDU_OCR_QUERY_URL, BAIDU_OCR_POLL_SECONDS, BAIDU_OCR_TIMEOUT_SECONDS, REQUEST_TIMEOUT_SECONDS

class BaiduOCRError(RuntimeError): pass

class BaiduPaddleOCRVL:
    provider_name="文档解析（PaddleOCR-VL）"
    def __init__(self, api_key:str, secret_key:str):
        self.api_key=api_key.strip(); self.secret_key=secret_key.strip()
        if not self.api_key or not self.secret_key: raise BaiduOCRError("百度云 OCR 需要 API Key 和 Secret Key。")

    async def token(self, client:httpx.AsyncClient)->str:
        res=await client.post(BAIDU_OCR_TOKEN_URL,params={"grant_type":"client_credentials","client_id":self.api_key,"client_secret":self.secret_key})
        data=res.json()
        if res.status_code>=400 or not data.get("access_token"):
            raise BaiduOCRError(f"百度云 OCR 鉴权失败：{data.get('error_description') or data.get('error_msg') or res.text[:300]}")
        return data["access_token"]

    async def test_credentials(self)->tuple[bool,str]:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                await self.token(client)
            return True,"百度智能云 OCR 鉴权成功；文档会在用户选择云端解析后发送至百度。"
        except Exception as exc:
            return False,str(exc)

    async def parse(self, file_path:str|Path)->ExtractedText:
        path=Path(file_path)
        if not path.exists(): raise BaiduOCRError("待解析文件不存在。")
        raw=path.read_bytes()
        async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS,read=BAIDU_OCR_TIMEOUT_SECONDS+30),follow_redirects=True) as client:
            token=await self.token(client)
            payload={
                "file_data":base64.b64encode(raw).decode("ascii"), "file_name":path.name,
                "analysis_chart":"true", "merge_tables":"true", "relevel_titles":"true", "return_span_boxes":"true",
            }
            response=await client.post(BAIDU_OCR_TASK_URL,params={"access_token":token},data=payload,headers={"Content-Type":"application/x-www-form-urlencoded"})
            data=response.json()
            task_id=(data.get("result") or {}).get("task_id")
            if response.status_code>=400 or not task_id or data.get("error_code",0):
                raise BaiduOCRError(f"百度文档解析提交失败：{data.get('error_msg') or data}")
            deadline=time.monotonic()+BAIDU_OCR_TIMEOUT_SECONDS
            while time.monotonic()<deadline:
                await asyncio.sleep(BAIDU_OCR_POLL_SECONDS)
                poll=await client.post(BAIDU_OCR_QUERY_URL,params={"access_token":token},data={"task_id":task_id},headers={"Content-Type":"application/x-www-form-urlencoded"})
                data=poll.json(); result=data.get("result") or {}; status=result.get("status")
                if status=="success":
                    url=result.get("parse_result_url")
                    if not url: raise BaiduOCRError("百度解析成功但未返回 parse_result_url。")
                    parsed=await client.get(url); parsed.raise_for_status()
                    return normalize_result(parsed.json())
                if status=="failed": raise BaiduOCRError(f"百度文档解析失败：{result.get('task_error') or data.get('error_msg') or '未知原因'}")
                if poll.status_code>=400: raise BaiduOCRError(f"百度任务查询失败：{data.get('error_msg') or poll.text[:300]}")
        raise BaiduOCRError("百度云 OCR 任务超时，请稍后重试。")

def normalize_result(payload:dict[str,Any])->ExtractedText:
    blocks=[]; pages=[]; all_text=[]; order=0
    for page in payload.get("pages",[]):
        page_no=int(page.get("page_num",0))+1
        table_map={t.get("layout_id"):t for t in page.get("tables",[])}
        page_text=[]
        for layout in page.get("layouts",[]):
            order+=1; kind=layout.get("type","text"); position=layout.get("position")
            if kind=="table":
                table=table_map.get(layout.get("layout_id"),{})
                text=table.get("markdown") or table.get("table_html") or ""
                cells=table.get("cells") or []
                matrix=table.get("matrix") or _matrix_from_cells(cells)
                blocks.append(LayoutBlock(order,"table",text,page_no,"正文",position,matrix))
                page_text.append(text)
            else:
                text=(layout.get("text") or "").strip()
                if text:
                    btype="heading" if kind in {"doc_title","paragraph_title"} else "paragraph"
                    blocks.append(LayoutBlock(order,btype,text,page_no,layout.get("sub_type") or "正文",position))
                    page_text.append(text)
        joined="\n".join(page_text); pages.append(PageContent(page_no,joined)) ; all_text.append(joined)
    return ExtractedText(text="\f".join(all_text),pages=pages,blocks=blocks,used_ocr=True,source_method="baidu_paddleocr_vl",parser_name="百度云 文档解析（PaddleOCR-VL）")

def _matrix_from_cells(cells:list[Any])->list[list[str]]:
    # API cells are rich layout objects; preserve a reasonable text matrix when row/col metadata is present.
    if not cells:return []
    rows=[]
    for row in cells:
        if isinstance(row,list): rows.append([str(c.get("text",c)) if isinstance(c,dict) else str(c) for c in row])
    return rows
