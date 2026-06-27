import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

// html: false means raw HTML in the model's output is escaped, not rendered.
// linkify: false stops false-positive auto-links (e.g. "payouts.No" → payouts.no).
// DOMPurify is then a second line of defence before the result is bound via v-html.
const md = new MarkdownIt({ html: false, linkify: false, breaks: true })

export function renderMarkdown(text: string): string {
  const rendered = md.render(text ?? '')
  if (typeof window === 'undefined') {
    // Server: the chat is client-only, so this is never shown to a user.
    return rendered
  }
  return DOMPurify.sanitize(rendered, { USE_PROFILES: { html: true } })
}
