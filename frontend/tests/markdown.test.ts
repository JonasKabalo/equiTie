import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../utils/markdown'

describe('renderMarkdown', () => {
  it('renders basic markdown', () => {
    expect(renderMarkdown('**bold**')).toContain('<strong>bold</strong>')
  })

  it('does not emit raw HTML tags from the model (html: false)', () => {
    const out = renderMarkdown('<img src=x onerror=alert(1)>')
    expect(out).not.toContain('<img')
  })

  it('never produces a javascript: link', () => {
    const out = renderMarkdown('[click](javascript:alert(1))')
    expect(out).not.toMatch(/href=["']?javascript:/i)
  })
})
