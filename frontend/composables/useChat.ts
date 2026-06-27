import { ref, watch } from 'vue'
import type { Citation } from '~/types/portfolio'
import { consumeSse } from '~/utils/sse'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  tools: string[]
  citations: Citation[]
  streaming: boolean
}

// Chat history is persisted to localStorage per investor so a refresh keeps the
// conversation. This is intentionally a client-only stopgap — a real product would
// persist conversations server-side (see ROADMAP.md).
const STORAGE_PREFIX = 'equitie-chat:'

function load(investorId: string): ChatMessage[] {
  if (typeof window === 'undefined') {
    return []
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + investorId)
    if (!raw) {
      return []
    }
    const parsed = JSON.parse(raw) as ChatMessage[]
    // Never restore a half-streamed message as "still streaming".
    return parsed.map(m => ({ ...m, streaming: false }))
  } catch {
    return []
  }
}

function save(investorId: string, messages: ChatMessage[]): void {
  if (typeof window === 'undefined') {
    return
  }
  try {
    window.localStorage.setItem(STORAGE_PREFIX + investorId, JSON.stringify(messages))
  } catch {
    // Quota or serialisation issue — non-fatal.
  }
}

export function useChat(getInvestorId: () => string) {
  const base = useApiBase()
  const messages = ref<ChatMessage[]>(load(getInvestorId()))
  const isStreaming = ref(false)

  watch(messages, () => save(getInvestorId(), messages.value), { deep: true })

  function clear(): void {
    messages.value = []
  }

  async function send(question: string): Promise<void> {
    const trimmed = question.trim()
    if (!trimmed || isStreaming.value) {
      return
    }

    messages.value.push({ role: 'user', content: trimmed, tools: [], citations: [], streaming: false })

    // Prior turns (everything before the message we just pushed) as plain text history.
    const history = messages.value
      .slice(0, -1)
      .map(m => ({ role: m.role, content: m.content }))

    messages.value.push({ role: 'assistant', content: '', tools: [], citations: [], streaming: true })
    // Grab the *reactive* element — mutating the raw object we pushed would not
    // trigger a re-render (it bypasses Vue's proxy).
    const assistant = messages.value[messages.value.length - 1]
    isStreaming.value = true

    try {
      const res = await fetch(`${base}/api/chat/${getInvestorId()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed, history }),
      })

      if (!res.ok || res.body === null) {
        assistant.content =
          res.status === 503
            ? '_The assistant is not available right now. Please contact support._'
            : `_Sorry, something went wrong (HTTP ${res.status})._`
        return
      }

      await consumeSse(res.body, (event, data) => {
        if (event === 'token') {
          assistant.content += String(data.text ?? '')
        } else if (event === 'tool') {
          assistant.tools.push(String(data.name ?? ''))
        } else if (event === 'done') {
          assistant.citations = (data.citations as Citation[] | undefined) ?? []
        }
      })
    } catch {
      if (!assistant.content) {
        assistant.content = '_Network error — is the backend running on port 8000?_'
      }
    } finally {
      assistant.streaming = false
      isStreaming.value = false
    }
  }

  return { messages, isStreaming, send, clear }
}
