/** Incremental SSE decoding, including CRLF, split UTF-8 and a final unterminated frame. */
export async function readEventStream(
  stream: ReadableStream<Uint8Array>,
  onFrame: (event: string, data: string) => boolean | void,
): Promise<void> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const dispatch = (frame: string) => {
    let event = 'message'
    const data: string[] = []
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''))
    }
    return data.length ? onFrame(event, data.join('\n')) : false
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let boundary: RegExpExecArray | null
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index)
        buffer = buffer.slice(boundary.index + boundary[0].length)
        if (dispatch(frame)) return
      }
      if (done) {
        if (buffer.trim()) dispatch(buffer)
        return
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
