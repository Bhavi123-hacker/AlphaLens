/** Graphic-only rounding to 4 decimal places. Tables preserve the original string. */
export function graphicNumber(value: string | number | null | undefined): number | null {
  if (value == null) return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (value.length > 300) return null
  const rational = /^(-?\d+)\/(\d+)$/.exec(value)
  const decimal = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  let numerator: bigint, denominator: bigint
  if (rational) { numerator = BigInt(rational[1]); denominator = BigInt(rational[2]) }
  else if (decimal) { const fraction = decimal[3] ?? ''; numerator = BigInt((decimal[1] || '') + decimal[2] + fraction); denominator = 10n ** BigInt(fraction.length) }
  else return null
  if (denominator === 0n) return null
  const sign = numerator < 0n ? -1n : 1n
  const scaled = ((numerator * sign * 10_000n + denominator / 2n) / denominator) * sign
  if ((scaled === 0n && numerator !== 0n) || scaled > BigInt(Number.MAX_SAFE_INTEGER) || scaled < BigInt(Number.MIN_SAFE_INTEGER)) return null
  return Number(scaled) / 10_000
}
export function exact(value: unknown): string {
  if (value == null) return 'Unavailable'
  if (typeof value === 'string') return value.replace(/^(-?\d+)(?=\.|$)/, (_, whole: string) => whole.replace(/\B(?=(\d{3})+(?!\d))/g, ','))
  return typeof value === 'number' && Number.isFinite(value) ? String(value) : 'Unavailable'
}
export function decimalHeadline(value: string | null | undefined): string {
  if (value == null) return 'Unavailable'
  // Removing trailing fractional zeroes changes no value; exact source text remains in the table.
  return exact(value.replace(/(\.\d*?[1-9])0+$|\.0+$/, '$1'))
}
export function metric(value: unknown, percent = false): string {
  return typeof value === 'number' && Number.isFinite(value) ? percent ? `${(value * 100).toFixed(2)}%` : value.toFixed(4) : 'Unavailable'
}
export function readable(value: string) { return value.replaceAll('_', ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()) }
export function rangeStart(end: string, range: string, first: string) {
  if (range === 'ALL') return first
  const date = new Date(end + 'T00:00:00Z')
  const months: Record<string, number> = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12, '3Y': 36, '5Y': 60 }
  const day = date.getUTCDate(); date.setUTCDate(1); date.setUTCMonth(date.getUTCMonth() - (months[range] ?? 12))
  const month = date.getUTCMonth(); date.setUTCDate(day); if (date.getUTCMonth() !== month) date.setUTCDate(0)
  return date.toISOString().slice(0, 10) < first ? first : date.toISOString().slice(0, 10)
}
export function partitionBacktests(rows: { cause_counts: Record<string, number>; status: string }[]) {
  const counts = { actions: 0, both: 0, gaps: 0, resolved: 0 }
  for (const row of rows) {
    if (row.status !== 'UNRESOLVED_ECONOMIC_OUTCOMES') { counts.resolved++; continue }
    const action = !!row.cause_counts.RAW_ACTION_UNRECONCILED_ECONOMIC_ENTITLEMENT
    const gap = Object.entries(row.cause_counts).some(([k, v]) => k !== 'RAW_ACTION_UNRECONCILED_ECONOMIC_ENTITLEMENT' && v > 0)
    if (action && gap) counts.both++; else if (action) counts.actions++; else if (gap) counts.gaps++
  }
  return counts
}
