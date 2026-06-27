// Minimal Server-Sent Events parser for the chat stream.

export type SsePayload = Record<string, unknown>
export type SseHandler = (event: string, data: SsePayload) => void

export function parseFrame(frame: string, onEvent: SseHandler): void {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }
  if (dataLines.length === 0) {
    return
  }
  try {
    onEvent(event, JSON.parse(dataLines.join('\n')) as SsePayload)
  } catch {
    // Ignore a malformed frame rather than break the stream.
  }
}

export async function consumeSse(
  body: ReadableStream<Uint8Array>,
  onEvent: SseHandler,
): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      parseFrame(buffer.slice(0, boundary), onEvent)
      buffer = buffer.slice(boundary + 2)
      boundary = buffer.indexOf('\n\n')
    }
  }
  if (buffer.trim().length > 0) {
    parseFrame(buffer, onEvent)
  }
}
