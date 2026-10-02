import test from 'node:test'
import assert from 'node:assert/strict'
import { readEventStream } from '../src/api/sse.ts'
import { streamMessage } from '../src/api/client.ts'

function stream(text, byteSize = 1) {
  const bytes = new TextEncoder().encode(text)
  return new ReadableStream({ start(controller) {
    for (let i = 0; i < bytes.length; i += byteSize) controller.enqueue(bytes.slice(i, i + byteSize))
    controller.close()
  } })
}

test('SSE supports split UTF-8, CRLF, comments, multiline data and final frames', async () => {
  const received = []
  const body = stream(': keepalive\r\n\r\nevent: delta\r\ndata: {"text":\r\ndata: "中文"}\r\n\r\nevent: done\ndata: {}')
  await readEventStream(body, (event, data) => { received.push([event, JSON.parse(data)]) })
  assert.deepEqual(received, [['delta', { text: '中文' }], ['done', {}]])
  assert.equal(body.locked, false)
})
test('the stream is cancelled and unlocked when a terminal event arrives', async () => {
  let cancelled = false
  const body = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('event: done\ndata: {}\n\n')) }, cancel() { cancelled = true } })
  await readEventStream(body, () => true)
  assert.equal(cancelled, true)
  assert.equal(body.locked, false)
})
test('a callback error also releases the stream', async () => {
  const body = stream('event: delta\ndata: invalid-json\n\n')
  await assert.rejects(readEventStream(body, (_event, data) => JSON.parse(data)), SyntaxError)
  assert.equal(body.locked, false)
})
test('client reports a truncated response while retaining delivered content', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response(stream('event: answer.delta\ndata: {"content":"已生成内容"}\n\n')))
  const events = []
  await assert.rejects(streamMessage('p', 'c', { question: '问题' }, event => events.push(event)), /连接已中断/)
  assert.deepEqual(events, [{ type: 'delta', content: '已生成内容' }])
})
test('completion without a final newline and citation metadata survive decoding', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response(stream('event: citation\r\ndata: {"number":9,"documentId":"doc","chunkId":"table"}\r\n\r\nevent: message.completed\r\ndata: {}')))
  const events = []
  await streamMessage('p', 'c', { question: '问题' }, event => events.push(event))
  assert.equal(events[0].citation.chunkId, 'table')
  assert.equal(events[0].citation.number, 9)
  assert.equal(events[1].type, 'completed')
})
test('server errors are terminal even if the connection remains open', async t => {
  const body = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('event: error\ndata: {"message":"失败"}\n\n')) } })
  t.mock.method(globalThis, 'fetch', async () => new Response(body))
  const events = []
  await streamMessage('p', 'c', { question: '问题' }, event => events.push(event))
  assert.deepEqual(events, [{ type: 'error', message: '失败' }])
})
