import { APIError } from '../api/client'

// Canceled pages can leave a bounded server read finishing. Retry only that capacity
// condition briefly; unavailable evidence and authorization failures stay explicit.
export function readRetry(count: number, error: Error): boolean {
  if (!(error instanceof APIError)) return false
  if (error.code === 'READ_CAPACITY' && error.status === 429) return count < 3
  return count < 1 && [0, 429, 502, 504].includes(error.status)
}
export function readRetryDelay(attempt: number, error: Error): number {
  return error instanceof APIError && error.code === 'READ_CAPACITY' ? Math.min(8000, 2000 * 2 ** attempt) : 1200
}
