from pathlib import Path

import pytest

from app import crud, models
from app.adapters.llm import LLMProvider, _citation_data
from app.services import document_files
from app.services.retrieval import retrieve_chunks


@pytest.mark.asyncio
async def test_original_file_download_and_relocated_upload(client, db_session):
    content = '原始文档内容，用于验证下载。'.encode()
    response = await client.post('/api/documents/upload', files={'files': ('原文.txt', content, 'text/plain')})
    doc_id = response.json()[0]['id']
    response = await client.get(f'/api/documents/{doc_id}/file')
    assert response.status_code == 200
    assert response.content == content
    assert response.headers['content-disposition'].startswith('attachment;')
    doc = await db_session.get(models.Document, doc_id)
    basename = Path(doc.storage_path).name
    doc.storage_path = f'D:\\old-project\\backend\\storage\\uploads\\{basename}'
    await db_session.commit()
    response = await client.get(f'/api/documents/{doc_id}/file')
    assert response.status_code == 200
    assert response.content == content
    # Re-parsing a moved file uses the same safe resolver.
    summary = await client.post(f'/api/documents/{doc_id}/summarize')
    assert summary.status_code == 200
    assert summary.json()['parseStatus'] == 'ready'


@pytest.mark.asyncio
async def test_original_file_missing_and_outside_upload_root(client, db_session, tmp_path):
    outside = tmp_path / 'private.txt'
    outside.write_text('must not be served')
    doc = await crud.create_document(db_session, {'file_name': 'private.txt', 'storage_path': str(outside), 'knowledge_base': 'general'})
    assert (await client.get(f'/api/documents/{doc.id}/file')).status_code == 404
    assert (await client.get('/api/documents/unknown/file')).status_code == 404


@pytest.mark.asyncio
async def test_original_pdf_supports_inline_and_range_requests(client):
    content = b'%PDF-1.4\n' + b'x' * 64
    uploaded = await client.post('/api/documents/upload', files={'files': ('source.pdf', content, 'application/pdf')})
    doc_id = uploaded.json()[0]['id']
    response = await client.get(f'/api/documents/{doc_id}/file', headers={'Range': 'bytes=0-7'})
    assert response.status_code == 206
    assert response.content == content[:8]
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['content-disposition'].startswith('inline;')


def test_path_traversal_and_missing_files_do_not_resolve(tmp_path, monkeypatch):
    root = tmp_path / 'uploads'
    root.mkdir()
    (tmp_path / 'secret.txt').write_text('secret')
    monkeypatch.setattr(document_files, 'UPLOAD_DIR', str(root))
    assert document_files.resolve_document_file(str(root / '..' / 'secret.txt')) is None
    assert document_files.resolve_document_file(None) is None
    assert document_files.resolve_document_file(str(root / 'missing.txt')) is None


@pytest.mark.asyncio
async def test_unrelated_tables_and_parent_chunks_are_not_retrieved(db_session):
    doc = await crud.create_document(db_session, {'file_name': '规划.docx', 'knowledge_base': 'general', 'parse_status': 'ready', 'is_usable': 1})
    db_session.add_all([
        models.DocumentChunk(document_id=doc.id, chunk_index=0, chunk_type='parent', text='人口规划标题'),
        models.DocumentChunk(document_id=doc.id, chunk_index=1, chunk_type='table', text='人口 | 31400'),
        models.DocumentChunk(document_id=doc.id, chunk_index=2, chunk_type='child', text='人口预测：31400人'),
    ])
    await db_session.commit()
    assert await retrieve_chunks(db_session, 'unused', '你是谁') == []
    assert await retrieve_chunks(db_session, 'unused', '你好') == []
    assert await retrieve_chunks(db_session, 'unused', '!!!') == []
    rows = await retrieve_chunks(db_session, 'unused', '人口')
    assert len(rows) == 2
    assert rows[0].chunk.chunk_type == 'table'
    assert all(row.chunk.chunk_type != 'parent' for row in rows)


def test_every_context_evidence_number_has_a_citation():
    chunks = [{'chunk_id': str(index), 'text': f'第{index}条'} for index in range(12)]
    citations = _citation_data(chunks)
    assert [item['number'] for item in citations] == list(range(1, 13))
    assert citations[-1]['chunk_id'] == '11'


@pytest.mark.asyncio
async def test_server_stream_failure_preserves_partial_answer(client, monkeypatch):
    project = (await client.post('/api/projects', json={'name': '中断测试'})).json()
    conversation = (await client.post(f"/api/projects/{project['id']}/conversations", json={'title': '测试'})).json()

    async def failing_stream(*args, **kwargs):
        yield '已经生成的部分回答'
        raise RuntimeError('测试连接中断')

    monkeypatch.setattr(LLMProvider, 'stream_chat', failing_stream)
    response = await client.post(f"/api/projects/{project['id']}/conversations/{conversation['id']}/messages/stream", json={'question': '问题'})
    assert 'event: error' in response.text
    stored = (await client.get(f"/api/conversations/{conversation['id']}")).json()['turns'][0]
    assert stored['status'] == 'failed'
    assert '已经生成的部分回答' in stored['answer']
    assert '测试连接中断' in stored['answer']
