import { describe, expect, it } from 'vitest'
import { type SsePayload, consumeSse, parseFrame } from '../utils/sse'

describe('sse', () => {
  it('parses a single frame', () => {
    const events: Array<[string, SsePayload]> = []
    parseFrame('event: token\ndata: {"text":"hi"}', (e, d) => events.push([e, d]))
    expect(events).toEqual([['token', { text: 'hi' }]])
  })

  it('consumes a stream split across chunk boundaries', async () => {
    const enc = new TextEncoder()
    const chunks = [
      'event: tool\ndata: {"name":"get_portfolio',
      '_overview"}\n\nevent: token\ndata: {"text":"He',
      'llo"}\n\nevent: done\ndata: {"citations":[]}\n\n',
    ]
    let i = 0
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i < chunks.length) {
          controller.enqueue(enc.encode(chunks[i++]))
        } else {
          controller.close()
        }
      },
    })

    const seen: string[] = []
    const tokens: string[] = []
    await consumeSse(stream, (event, data) => {
      seen.push(event)
      if (event === 'token') {
        tokens.push(String(data.text))
      }
    })

    expect(seen).toEqual(['tool', 'token', 'done'])
    expect(tokens.join('')).toBe('Hello')
  })
})
