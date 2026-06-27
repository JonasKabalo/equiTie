export function formatCurrency(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(value)
  } catch {
    return `${currency} ${formatNumber(value)}`
  }
}

export function formatNumber(value: number, digits = 0): string {
  return new Intl.NumberFormat('en-GB', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value)
}

export function formatMoic(value: number | null): string {
  return value == null ? 'n/a' : `${value.toFixed(2)}×`
}

export function formatPercent(value: number | null): string {
  return value == null ? 'n/a' : `${(value * 100).toFixed(0)}%`
}
