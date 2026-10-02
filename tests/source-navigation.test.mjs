import test from 'node:test'
import assert from 'node:assert/strict'
import { locateCitation, findCitationDocument, findCitationInReuploads, parseTableRows } from '../src/lib/citationLocation.ts'
import { ApiError, getDocument, getDocumentFileUrl } from '../src/api/client.ts'

const first = { id: 'first', chunkType: 'child', text: '封面', section: '正文' }
const table = { id: 'table', parentId: 'parent', chunkType: 'table', text: '| 专项规划 | 衔接情况 |\n| 城乡消防专项规划 | 已衔接 |', section: '专项规划' }
const chunks = [first, { id: 'parent', chunkType: 'parent', text: '专项规划' }, table]

test('a table citation selects the exact block instead of the document cover', () => {
  assert.deepEqual(locateCitation(chunks, { chunkId: 'table', quote: '已衔接' }), { chunkId: 'table', match: 'id' })
})
test('old parent references resolve to a visible child', () => {
  assert.equal(locateCitation(chunks, { chunkId: 'parent', quote: '已衔接' }).chunkId, 'table')
})
test('re-parsed documents resolve old IDs using normalized quotation text', () => {
  assert.deepEqual(locateCitation(chunks, { chunkId: 'removed', quote: '城乡消防专项规划  已衔接' }), { chunkId: 'table', match: 'quote' })
})
test('section fallback is distinguished from an exact text match', () => {
  assert.deepEqual(locateCitation(chunks, { section: '专项规划', quote: '旧版本内容' }), { chunkId: 'table', match: 'section' })
  assert.equal(locateCitation(chunks, { section: '正文', quote: '未找到的文字' }), null)
  assert.equal(locateCitation(chunks), null)
})
test('explicit document IDs never fall back to a different same-name file', () => {
  const docs = [{ id: 'new', fileName: '规划.docx', knowledgeBase: 'project' }]
  assert.equal(findCitationDocument(docs, { documentId: 'deleted', documentName: '规划.docx' }), undefined)
})
test('legacy filename references must uniquely identify a document', () => {
  const doc = { id: 'one', fileName: '规划.docx', knowledgeBase: 'project' }
  const citation = { documentName: '规划.docx', knowledgeBase: 'project' }
  assert.equal(findCitationDocument([doc], citation), doc)
  assert.equal(findCitationDocument([doc, { ...doc, id: 'two' }], citation), undefined)
  assert.equal(findCitationDocument([{ ...doc, fileName: '旧规划.docx' }], citation), undefined)
})
test('deleted citations recover only a unique quotation in the same project and knowledge base', () => {
  const citation = { documentId: 'old', documentName: '规划.docx', knowledgeBase: 'project', quote: '落实高原地区重要交通节点建设和公共服务设施布局要求。' }
  const current = { id: 'new', fileName: '规划.docx', knowledgeBase: 'project', projectId: 'p1', parseStatus: 'ready', isUsable: true }
  const otherProject = { ...current, id: 'other-project', projectId: 'p2' }
  const general = { ...current, id: 'general', knowledgeBase: 'general', projectId: undefined }
  const blocks = new Map([
    ['new', [{ id: 'new-chunk', chunkType: 'child', text: '规划要求：落实高原地区重要交通节点建设和公共服务设施布局要求。' }]],
    ['other-project', [{ id: 'other-chunk', chunkType: 'child', text: citation.quote }]],
    ['general', [{ id: 'general-chunk', chunkType: 'child', text: citation.quote }]],
  ])
  assert.deepEqual(findCitationInReuploads([current, otherProject, general], citation, 'p1', blocks), { document: current, chunkId: 'new-chunk' })
  assert.equal(findCitationInReuploads([otherProject, general], citation, 'p1', blocks), undefined)
})

test('deleted citations do not guess when text changed, is short, or appears twice', () => {
  const doc = { id: 'new', fileName: '规划.docx', knowledgeBase: 'project', projectId: 'p1', parseStatus: 'ready', isUsable: true }
  const quote = '落实高原地区重要交通节点建设和公共服务设施布局要求。'
  const citation = { documentId: 'old', documentName: doc.fileName, knowledgeBase: 'project', quote }
  assert.equal(findCitationInReuploads([doc], citation, 'p1', new Map([['new', [{ id: 'a', chunkType: 'child', text: '内容已改写。' }]]])), undefined)
  assert.equal(findCitationInReuploads([doc], { ...citation, quote: '一般要求' }, 'p1', new Map([['new', [{ id: 'a', chunkType: 'child', text: '一般要求' }]]])), undefined)
  assert.equal(findCitationInReuploads([doc], citation, 'p1', new Map([['new', [
    { id: 'a', chunkType: 'child', text: quote },
    { id: 'b', chunkType: 'child', text: quote },
  ]]])), undefined)
  assert.equal(findCitationInReuploads([{ ...doc, id: 'old' }], citation, 'p1', new Map([['old', [{ id: 'a', chunkType: 'child', text: quote }]]])), undefined)
})

test('document lookup exposes HTTP status so only a missing original can recover', async () => {
  const originalFetch = globalThis.fetch
  try {
    for (const status of [404, 500]) {
      globalThis.fetch = async () => new Response(JSON.stringify({ detail: '读取失败' }), { status, headers: { 'Content-Type': 'application/json' } })
      await assert.rejects(getDocument('old'), error => error instanceof ApiError && error.status === status)
    }
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('invalid or object-based OCR tables fall back safely to text', () => {
  for (const value of ['null', '{', '{"rows":{}}', '{"cells":[{"text":"甲"}]}', '{"rows":[]}']) assert.equal(parseTableRows(value), null)
  assert.deepEqual(parseTableRows('{"rows":[["类别", "数量"],[{"text":"人口"},31400]]}'), [['类别', '数量'], ['人口', '31400']])
})
test('original PDF opens at its page, Office downloads, web sources only allow HTTP(S)', () => {
  assert.equal(getDocumentFileUrl({ id: 'doc', fileType: 'pdf' }, 9), '/api/documents/doc/file#page=9')
  assert.equal(getDocumentFileUrl({ id: 'doc', fileType: 'word' }, 9), '/api/documents/doc/file')
  assert.equal(getDocumentFileUrl({ id: 'doc', fileType: 'web', sourceUrl: 'https://example.test/source' }), 'https://example.test/source')
  assert.equal(getDocumentFileUrl({ id: 'doc', fileType: 'web', sourceUrl: 'javascript:alert(1)' }), '/api/documents/doc/file')
})
