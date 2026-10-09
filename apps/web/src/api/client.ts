import { z } from 'zod'
import { envelope, type Evidence } from './contracts'

export class APIError extends Error {
  readonly status: number
  readonly code: string
  readonly reasons: string[]
  readonly evidence?: Evidence<unknown>
  constructor(status: number, code: string, message: string, reasons: string[] = [], evidence?: Evidence<unknown>) {
    super(message); this.name = 'APIError'; this.status = status; this.code = code; this.reasons = reasons; this.evidence = evidence
  }
}
// Queue reads instead of exceeding the backend's two concurrent read permits.
let active = 0
const pending: Array<() => void> = []
async function permit(signal?: AbortSignal) {
  await new Promise<void>((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException('Aborted', 'AbortError')); return }
    const run = () => {
      if (signal?.aborted) { reject(new DOMException('Aborted', 'AbortError')); advance(); return }
      active++; resolve()
    }
    if (active < 2) run(); else pending.push(run)
  })
}
function advance() { if (active < 2) pending.shift()?.() }
export function queryString(values: Record<string, string | number | undefined>) {
  const result = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) if (value !== undefined && value !== '') result.set(key, String(value))
  return result.toString()
}
export function validateRange(start?: string, end?: string) {
  for (const date of [start, end]) if (date && (!/^\d{4}-\d{2}-\d{2}$/.test(date) || new Date(date + 'T00:00:00Z').toISOString().slice(0, 10) !== date))
    throw new APIError(422, 'INVALID_DATE_RANGE', 'Choose valid session dates.')
  if (start && end && start > end) throw new APIError(422, 'INVALID_DATE_RANGE', 'Start date must precede end date.')
}
export async function get<S extends z.ZodType>(path: string, schema: S, signal?: AbortSignal): Promise<Evidence<z.infer<S>>> {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('://')) throw new APIError(422, 'INVALID_ROUTE', 'Use a local API route.')
  await permit(signal)
  const controller = new AbortController()
  const cancel = () => controller.abort()
  signal?.addEventListener('abort', cancel, { once: true })
  if (signal?.aborted) controller.abort()
  const timeout = setTimeout(cancel, 40_000)
  try {
    const response = await fetch(`/api/v1${path}`, { method: 'GET', signal: controller.signal, credentials: 'omit', headers: { Accept: 'application/json' } })
    const length = Number(response.headers.get('content-length') ?? '0')
    if (length > 2_000_000) throw new APIError(413, 'RESPONSE_LIMIT', 'This response exceeds the local read budget.')
    const text = await response.text()
    if (text.length > 2_000_000) throw new APIError(413, 'RESPONSE_LIMIT', 'This response exceeds the local read budget.')
    let raw: unknown
    try { raw = JSON.parse(text) } catch { throw new APIError(response.status || 502, 'BACKEND_RESPONSE_INVALID', 'The backend did not return a valid API response.') }
    if (!response.ok) {
      const evidence = envelope(z.unknown()).safeParse(raw)
      const err = z.object({ error_code: z.string(), message: z.string() }).safeParse(raw)
      throw new APIError(response.status, err.success ? err.data.error_code : 'EVIDENCE_UNAVAILABLE',
        err.success ? err.data.message : 'Required evidence is unavailable.', evidence.success ? evidence.data.missing_data_reasons : [], evidence.success ? evidence.data : undefined)
    }
    const parsed = envelope(schema).safeParse(raw)
    if (!parsed.success) throw new APIError(502, 'CONTRACT_MISMATCH', 'The API response does not match the verified P17 contract.')
    return parsed.data as Evidence<z.infer<S>>
  } catch (error) {
    if (error instanceof APIError) throw error
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    throw new APIError(controller.signal.aborted ? 504 : 0, controller.signal.aborted ? 'TIMEOUT' : 'BACKEND_DISCONNECTED',
      controller.signal.aborted ? 'The read timed out. Narrow the date range and retry.' : 'The local backend is disconnected. Start P17 and retry.')
  } finally { clearTimeout(timeout); signal?.removeEventListener('abort', cancel); active--; advance() }
}
export async function collect<S extends z.ZodType>(path: string, schema: S, query: Record<string, string | number | undefined>, signal?: AbortSignal, cap = 5000) {
  let offset = 0
  const rows: z.infer<S>[] = []
  let last: Evidence<z.infer<S>[]> | undefined
  do {
    last = await get(`${path}?${queryString({ ...query, limit: Math.min(500, cap - offset), offset })}`, z.array(schema), signal)
    rows.push(...last.data); offset += last.data.length
    if (last.page?.has_more && last.data.length === 0) throw new APIError(502, 'PAGINATION_INVALID', 'The backend returned an inconsistent page.')
  } while (last.page?.has_more && offset < cap)
  return { ...last, data: rows, truncated: !!last.page?.has_more }
}
