"""Encrypted provider configuration, including explicit cloud OCR consent."""
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud
from ..adapters.llm import LLMProvider
from ..adapters.search import SearchProvider,SearchProviderError
from ..services.baidu_ocr import BaiduPaddleOCRVL
from ..schemas import ProviderConfigOut,ProviderConfigSave,ProviderConfigTest,ProviderConfigTestResponse,SearchConfigTest,OCRConfigTest
router=APIRouter(prefix="/provider-configs",tags=["provider-configs"])
@router.get("",response_model=list[ProviderConfigOut])
async def list_configs(db:AsyncSession=Depends(get_db)):return await crud.list_provider_configs(db)
@router.post("",response_model=ProviderConfigOut,status_code=201)
async def save_config(body:ProviderConfigSave,db:AsyncSession=Depends(get_db)):
    try:return await crud.save_provider_config(db,body.model_dump())
    except ValueError as exc:raise HTTPException(422,str(exc))
@router.post("/test",response_model=ProviderConfigTestResponse)
async def test_config(body:ProviderConfigTest):
    ok,message=await LLMProvider.test_connection(body.model_dump());return ProviderConfigTestResponse(ok=ok,message=message,search_tested=False)
@router.post("/test-search",response_model=ProviderConfigTestResponse)
async def test_search(body:SearchConfigTest):
    try:
        rows=await SearchProvider.search("国土空间规划",provider_config=body.model_dump())
        return ProviderConfigTestResponse(ok=True,message=f"联网搜索连接成功，真实返回 {len(rows)} 条结果。",search_tested=True)
    except SearchProviderError as exc:return ProviderConfigTestResponse(ok=False,message=str(exc),search_tested=True)
    except Exception as exc:return ProviderConfigTestResponse(ok=False,message=f"联网搜索连接失败：{exc}",search_tested=True)
@router.post("/test-baidu-ocr",response_model=ProviderConfigTestResponse)
async def test_baidu_ocr(body:OCRConfigTest):
    if not body.risk_confirmed:return ProviderConfigTestResponse(ok=False,message="请先确认：文件会发送至百度智能云进行云端解析。",search_tested=False)
    ok,message=await BaiduPaddleOCRVL(body.baidu_api_key,body.baidu_secret_key).test_credentials();return ProviderConfigTestResponse(ok=ok,message=message,search_tested=False)
