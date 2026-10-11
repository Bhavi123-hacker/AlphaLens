import { z } from 'zod'
import { envelope, type Evidence } from './contracts'

let csrfToken: string | undefined
let sessionEpoch = 0
export function setSessionContext(token?: string) { csrfToken = token; sessionEpoch++ }
export function expireSession() { setSessionContext(); window.dispatchEvent(new Event('alphalens:session-expired')) }
export async function authRequest<S extends z.ZodType>(path: string, schema: S, body?: unknown): Promise<z.infer<S>> {
  if (!/^\/auth\/(login|session|logout|password|sessions|sessions\/revoke)$/.test(path)) throw new APIError(422, 'INVALID_AUTH_ROUTE', 'Use a local account route.')
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 15_000)
  try {
    const response = await fetch(`/api/v1${path}`, { method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', signal: controller.signal,
      headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json', 'X-AlphaLens-Local': 'p21', ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}) }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
    if (!response.ok) {
      if (response.status === 401 && path !== '/auth/login' && path !== '/auth/session') expireSession()
      throw new APIError(response.status, 'AUTH_REQUEST_REJECTED', response.status === 429 ? 'Too many attempts. Wait five minutes before retrying.' : response.status === 401 ? 'Sign-in failed or the session expired.' : 'The local security request was rejected. Check setup, password policy and connection.')
    }
    const text = await response.text()
    if (text.length > 65536) throw new APIError(413, 'AUTH_RESPONSE_LIMIT', 'Security response exceeded its bound.')
    let raw: unknown
    try { raw = JSON.parse(text) } catch { throw new APIError(502, 'AUTH_CONTRACT_MISMATCH', 'The local account response was invalid.') }
    const result = schema.safeParse(raw)
    if (!result.success) throw new APIError(502, 'AUTH_CONTRACT_MISMATCH', 'The local account response was invalid.')
    return result.data
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(controller.signal.aborted ? 504 : 0, 'AUTH_CONNECTION_FAILED', 'The local account service is unavailable. Check the backend and retry.')
  } finally { clearTimeout(timeout) }
}

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
async function request<S extends z.ZodType>(path: string, schema: S, signal?: AbortSignal, body?: unknown): Promise<Evidence<z.infer<S>>> {
  const epoch = sessionEpoch
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('://')) throw new APIError(422, 'INVALID_ROUTE', 'Use a local API route.')
  await permit(signal)
  const controller = new AbortController()
  const cancel = () => controller.abort()
  signal?.addEventListener('abort', cancel, { once: true })
  if (signal?.aborted) controller.abort()
  const timeout = setTimeout(cancel, 40_000)
  try {
    if (epoch !== sessionEpoch) throw new APIError(401, 'SESSION_CHANGED', 'The workspace session changed.')
    const response = await fetch(`/api/v1${path}`, { method: body === undefined ? 'GET' : 'POST', signal: controller.signal, credentials: 'same-origin', headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json', 'X-AlphaLens-Local': 'p20', ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
    const length = Number(response.headers.get('content-length') ?? '0')
    if (length > 2_000_000) throw new APIError(413, 'RESPONSE_LIMIT', 'This response exceeds the local read budget.')
    const text = await response.text()
    if (epoch !== sessionEpoch) throw new APIError(401, 'SESSION_CHANGED', 'The workspace session changed.')
    if (text.length > 2_000_000) throw new APIError(413, 'RESPONSE_LIMIT', 'This response exceeds the local read budget.')
    let raw: unknown
    try { raw = JSON.parse(text) } catch { throw new APIError(response.status || 502, 'BACKEND_RESPONSE_INVALID', 'The backend did not return a valid API response.') }
    if (!response.ok) {
      if (response.status === 401) expireSession()
      const evidence = envelope(z.unknown()).safeParse(raw)
      const err = z.object({ error_code: z.string(), message: z.string() }).safeParse(raw)
      throw new APIError(response.status, err.success ? err.data.error_code : 'EVIDENCE_UNAVAILABLE',
        err.success ? err.data.message : 'Required evidence is unavailable.', evidence.success ? evidence.data.missing_data_reasons : [], evidence.success ? evidence.data : undefined)
    }
    const parsed = envelope(schema).safeParse(raw)
    if (!parsed.success) throw new APIError(502, 'CONTRACT_MISMATCH', 'The API response does not match the verified P17 contract.')
    window.dispatchEvent(new Event('alphalens:authenticated-read'))
    return parsed.data as Evidence<z.infer<S>>
  } catch (error) {
    if (error instanceof APIError) throw error
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    throw new APIError(controller.signal.aborted ? 504 : 0, controller.signal.aborted ? 'TIMEOUT' : 'BACKEND_DISCONNECTED',
      controller.signal.aborted ? 'The read timed out. Narrow the date range and retry.' : 'The local backend is disconnected. Start P17 and retry.')
  } finally { clearTimeout(timeout); signal?.removeEventListener('abort', cancel); active--; advance() }
}
export function get<S extends z.ZodType>(path: string, schema: S, signal?: AbortSignal): Promise<Evidence<z.infer<S>>> {
  return request(path, schema, signal)
}
export function post<S extends z.ZodType>(path: string, schema: S, body: unknown): Promise<Evidence<z.infer<S>>> {
  if (path !== '/alerts/preferences' && !/^\/alerts\/[a-f0-9]{64}\/state$/.test(path))
    return Promise.reject(new APIError(422, 'ALERT_WRITE_ROUTE_REQUIRED', 'Only local notification controls can be updated.'))
  if (body === undefined || (JSON.stringify(body)?.length ?? 8193) > 8192)
    return Promise.reject(new APIError(422, 'ALERT_WRITE_BODY_INVALID', 'Use a bounded notification control payload.'))
  return request(path, schema, undefined, body)
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
