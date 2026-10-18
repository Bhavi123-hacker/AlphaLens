export function object(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
export function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}
export function numeric(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}
export function percent(value: unknown, ratio = false): string {
  const number = numeric(value)
  return number === null ? 'Unavailable' : `${(number * (ratio ? 100 : 1)).toFixed(2)}%`
}
export function modelScore(value: unknown): string {
  const number = numeric(value)
  return number === null ? 'No compatible saved score' : number.toFixed(6)
}
export function text(value: unknown, fallback = 'Not observed'): string {
  return typeof value === 'string' && value.length ? value : fallback
}
