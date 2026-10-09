import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { collect, get } from '../src/api/client'

// Explicitly TEST_ONLY response fixtures, isolated from the application bundle.
function response(data: unknown, extra = {}) { return { data, source: 'TEST_ONLY_API_FIXTURE', as_of_session: null,
  classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null,
    p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, version: 'TEST_ONLY', artifact_id: null,
  provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null, ...extra } }
afterEach(() => vi.unstubAllGlobals())
describe('read-only typed API client', () => {
  it('retains source classification and only issues GET without credentials', async () => {
    const mock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response({ value: 1 })))); vi.stubGlobal('fetch', mock)
    const result = await get('/health', z.object({ value: z.number() })); expect(result.classification.usage_classification).toBe('TEST_ONLY')
    expect(mock.mock.calls[0][1]).toMatchObject({ method: 'GET', credentials: 'omit' })
  })
  it('preserves 503 unavailable reasons instead of creating a successful dataset', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(response(null, { evidence_status: 'UNAVAILABLE', missing_data_reasons: ['NO_PERSISTED_REAL_CURRENT_SESSION_OUTPUTS'] })), { status: 503 })))
    await expect(get('/signals', z.unknown())).rejects.toMatchObject({ status: 503, code: 'EVIDENCE_UNAVAILABLE', reasons: ['NO_PERSISTED_REAL_CURRENT_SESSION_OUTPUTS'] })
  })
  it.each([404, 422, 503])('preserves structured HTTP %i errors', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error_code: 'TEST_ONLY_ERROR', message: 'Explicit unavailable fixture' }), { status })))
    await expect(get('/stocks/test', z.unknown())).rejects.toMatchObject({ status, code: 'TEST_ONLY_ERROR' })
  })
  it('reports backend disconnection without a sample fallback', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network error'))); await expect(get('/health', z.unknown())).rejects.toMatchObject({ status: 0, code: 'BACKEND_DISCONNECTED' })
  })
  it('rejects incompatible successful payloads', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(response({ value: 'wrong type' }))))); await expect(get('/health', z.object({ value: z.number() }))).rejects.toMatchObject({ code: 'CONTRACT_MISMATCH' })
  })
  it('collects bounded pages with the existing offset convention', async () => {
    const mock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(response([1, 2], { page: { limit: 500, offset: 0, has_more: true, total: 3 } }))))
      .mockResolvedValueOnce(new Response(JSON.stringify(response([3], { page: { limit: 498, offset: 2, has_more: false, total: 3 } })))); vi.stubGlobal('fetch', mock)
    const result = await collect('/research/backtests', z.number(), {}, undefined, 500); expect(result.data).toEqual([1, 2, 3]); expect(mock.mock.calls[1][0]).toContain('offset=2')
  })
  it('marks truncated histories at the configured resource cap', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(response([1, 2], { page: { limit: 2, offset: 0, has_more: true, total: null } }))))); expect((await collect('/stocks/test/history', z.number(), {}, undefined, 2)).truncated).toBe(true)
  })
  it('rejects external and protocol-relative routes', async () => { await expect(get('//example.invalid', z.unknown())).rejects.toMatchObject({ code: 'INVALID_ROUTE' }) })
  it('honors already cancelled requests without making a fetch', async () => {
    const mock = vi.fn(); vi.stubGlobal('fetch', mock); const controller = new AbortController(); controller.abort()
    await expect(get('/health', z.unknown(), controller.signal)).rejects.toMatchObject({ name: 'AbortError' }); expect(mock).not.toHaveBeenCalled()
  })
})
