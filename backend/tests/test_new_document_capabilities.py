"""Regression tests added for V8 planning-document upgrades."""
from __future__ import annotations
import io
from pathlib import Path
import pytest
from app.services.text_extractor import extract_text
from app.config import BAIDU_OCR_TASK_URL, BAIDU_OCR_QUERY_URL, BAIDU_OCR_TOKEN_URL

PLANNING = Path('/mnt/data/7-10色塘片区国土空间总体规划汇总7.8(1)(1)(1).docx')

def test_baidu_paddleocr_vl_contract_and_no_local_ocr_dependency():
    assert BAIDU_OCR_TOKEN_URL.endswith('/oauth/2.0/token')
    assert BAIDU_OCR_TASK_URL.endswith('/paddle-vl-parser/task')
    assert BAIDU_OCR_QUERY_URL.endswith('/paddle-vl-parser/task/query')
    source = Path(__file__).parents[1] / 'app/services/text_extractor.py'
    text = source.read_text(encoding='utf-8')
    assert 'pytesseract' not in text
    assert 'import pytesseract' not in text
    assert 'pdf2image' not in text

@pytest.mark.skipif(not PLANNING.exists(), reason='uploaded planning document is unavailable')
def test_real_planning_docx_reading_order_and_tables():
    extracted = extract_text(str(PLANNING), 'word')
    assert extracted.parser_name == 'python-docx/OOXML-body-order'
    assert len(extracted.blocks) == 521
    tables = [b for b in extracted.blocks if b.block_type == 'table']
    assert len(tables) == 30
    assert [b.order for b in extracted.blocks] == sorted(b.order for b in extracted.blocks)
    assert any('常住人口31400人' in b.text for b in extracted.blocks)
    assert any('耕地保有量' in b.text for b in tables)
    assert any('现代农业园区' in b.text for b in tables)

@pytest.mark.asyncio
async def test_resumable_upload_can_be_cancelled(client):
    init = await client.post('/api/documents/uploads/init', json={'fileName': 'cancel.txt', 'totalBytes': 11})
    assert init.status_code == 201
    upload_id = init.json()['id']
    chunk = await client.put(f'/api/documents/uploads/{upload_id}/chunk?offset=0', content=b'hello')
    assert chunk.status_code == 200
    cancelled = await client.post(f'/api/documents/uploads/{upload_id}/cancel')
    assert cancelled.status_code == 200 and cancelled.json()['ok'] is True
    blocked = await client.put(f'/api/documents/uploads/{upload_id}/chunk?offset=5', content=b' world')
    assert blocked.status_code == 409

@pytest.mark.asyncio
async def test_real_planning_document_is_usable_for_structured_qa(client):
    if not PLANNING.exists():
        pytest.skip('uploaded planning document is unavailable')
    project = (await client.post('/api/projects', json={'name':'色塘片区真实文档回归'})).json()
    uploaded = await client.post(
        '/api/documents/upload',
        files={'files': (PLANNING.name, PLANNING.read_bytes(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},
        data={'knowledgeBase':'project', 'projectId':project['id']},
    )
    assert uploaded.status_code == 201
    doc = uploaded.json()[0]
    assert doc['parseStatus'] == 'ready'
    assert doc['tableCount'] == 30
    assert doc['parserName'] == 'python-docx/OOXML-body-order'
    conversation = (await client.post(f"/api/projects/{project['id']}/conversations", json={'title':'真实文档问答'})).json()
    answer = await client.post(f"/api/conversations/{conversation['id']}/messages", json={'question':'到2035年常住人口是多少？', 'knowledgeSource':'project'})
    assert answer.status_code == 201
    assert '31400' in answer.json()['answer']
    assert len(answer.json()['citations']) > 0

@pytest.mark.asyncio
async def test_baidu_save_requires_network_risk_confirmation(client):
    rejected = await client.post('/api/provider-configs', json={
        'provider':'DeepSeek', 'baiduApiKey':'demo-key', 'baiduSecretKey':'demo-secret',
        'ocrRiskConfirmed': False,
    })
    assert rejected.status_code == 422
