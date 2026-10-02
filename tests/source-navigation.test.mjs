import test from 'node:test'
import assert from 'node:assert/strict'
import { locateCitation, findCitationDocument, parseTableRows } from '../src/lib/citationLocation.ts'
import { getDocumentFileUrl } from '../src/api/client.ts'

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
