import { describe, expect, it } from 'vitest'
import { formatCurrency, formatMoic, formatNumber } from '../utils/format'

describe('format', () => {
  it('formats MOIC with a multiple sign', () => {
    expect(formatMoic(2)).toBe('2.00×')
    expect(formatMoic(null)).toBe('n/a')
  })

  it('groups numbers', () => {
    expect(formatNumber(1234567)).toBe('1,234,567')
  })

  it('formats currency and falls back on a bad code', () => {
    expect(formatCurrency(1000, 'USD')).toContain('1,000')
    expect(formatCurrency(1000, 'NOPE')).toContain('NOPE')
  })
})
