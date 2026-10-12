import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DailyResearch } from '../src/components/DailyResearch'
import { dailyStatusSchema } from '../src/api/daily'

// Explicit TEST_ONLY response; never a runtime fallback.
const status = { configured: true, pipeline_status: 'BLOCKED_SOURCE', live_data_activation: 'BLOCKED', scheduled_execution: 'DISABLED', latest_attempted_session: '2026-10-08', latest_successful_research_session: null, last_source_receipt: null, freshness: 'UNAVAILABLE', feature_readiness: 'UNAVAILABLE', inference_readiness: 'UNAVAILABLE', ranking_status: 'UNAVAILABLE', signal_status: 'UNAVAILABLE', historical_replay_count: 1, provider: { status: 'SOURCE_NOT_CLEARED', revision: 'TEST_ONLY', reasons: ['ONGOING_AUTOMATION_RIGHTS_NOT_ESTABLISHED'] }, production_ready: false }
const prospective = { configured: false, forecasts: 0, pending: 0, resolved: 0, unresolved: 0, metrics: null, inference: 'UNAVAILABLE', shortlist: 'UNAVAILABLE', scheduler: 'DISABLED', reasons: ['CROSS_SECTIONAL_FEATURE_EVIDENCE_NOT_VERIFIED'] }
function response(data: unknown) { return new Response(JSON.stringify({ data, source: 'TEST_ONLY', version: 'TEST_ONLY', as_of_session: null, artifact_id: null, classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null })) }
afterEach(() => vi.unstubAllGlobals())
it('preserves blocked activation and distinguishes replay from daily success', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => response(url.includes('/prospective/') ? prospective : url.includes('/runs') ? [] : status)))
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><DailyResearch timeline /></QueryClientProvider>)
  expect(await screen.findByText('Daily activation blocked')).toBeInTheDocument()
  expect(await screen.findByText('1 · not new market observations')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /execute|run pipeline|buy|sell/i })).not.toBeInTheDocument()
  expect(await screen.findByText('Daily shortlist unavailable')).toBeInTheDocument()
  expect(screen.getByText('Not initialized')).toBeInTheDocument()
})
it('rejects an incorrectly activated or production-ready status', () => {
  expect(dailyStatusSchema.safeParse({ ...status, production_ready: true }).success).toBe(false)
  expect(dailyStatusSchema.safeParse({ ...status, live_data_activation: 'PASSED' }).success).toBe(false)
})
it('renders backend disconnection without manufactured market values', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('TEST_ONLY disconnected')))
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><DailyResearch /></QueryClientProvider>)
  expect((await screen.findAllByText(/local backend is disconnected/)).length).toBeGreaterThan(0)
  expect(screen.queryByText('Daily activation blocked')).not.toBeInTheDocument()
})
