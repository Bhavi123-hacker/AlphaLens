import { expect, it } from 'vitest'
import { APIError } from '../src/api/client'
import { readRetry, readRetryDelay } from '../src/lib/readPolicy'

it('cold read-capacity retries are bounded and never hide unavailable or unauthorized evidence', () => {
  const capacity = new APIError(429, 'READ_CAPACITY', 'TEST_ONLY capacity')
  expect([0, 1, 2, 3].map(c => readRetry(c, capacity))).toEqual([true, true, true, false])
  expect([0, 1, 2, 3].map(c => readRetryDelay(c, capacity))).toEqual([2000, 4000, 8000, 8000])
  for (const status of [401, 403, 503]) expect(readRetry(0, new APIError(status, 'TEST_ONLY', 'TEST_ONLY unavailable'))).toBe(false)
  expect(readRetry(1, new APIError(504, 'TIMEOUT', 'TEST_ONLY timeout'))).toBe(false)
})
