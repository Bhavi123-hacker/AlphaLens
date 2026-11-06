import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Operations } from '../src/components/Operations'
import { APIError } from '../src/api/client'
import * as client from '../src/api/client'

// TEST_ONLY operational component responses; no application fallback or market rows.
afterEach(() => vi.restoreAllMocks())
function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Operations /></QueryClientProvider>)
}
it('renders actual supplied statuses and bounded measured latency samples', async () => {
  vi.spyOn(client, 'get').mockImplementation(async (path) => ({ data: path.includes('metrics') ? {
    scope: 'CURRENT_API_PROCESS', errors: 2, denied: 1, requests: { auth: { count: 10, retained_samples: 10, p50_ms: 4, p95_ms: 8 } },
  } : { observed_at: '2026-10-11T10:00:00Z', status: 'DEGRADED', production_ready: false, probe_duration_ms: 2,
    components: { live_source: { status: 'BLOCKED_BY_POLICY', reason: 'NO_APPROVED_ONGOING_SOURCE' } } },
  }) as never)
  mount()
  expect(await screen.findByText('Blocked by policy')).toBeInTheDocument()
  expect(await screen.findByText('8.0 ms')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Refresh system status' })).toBeInTheDocument()
})
it('shows unavailable diagnostics without constructing healthy results', async () => {
  vi.spyOn(client, 'get').mockRejectedValue(new APIError(503, 'OPERATIONS_UNAVAILABLE', 'TEST_ONLY unavailable'))
  mount()
  expect((await screen.findAllByText('TEST_ONLY unavailable')).length).toBe(2)
  expect(screen.queryByText('HEALTHY')).not.toBeInTheDocument()
})
