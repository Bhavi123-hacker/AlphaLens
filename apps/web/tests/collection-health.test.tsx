import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CollectionHealth } from '../src/components/CollectionHealth'

// TEST_ONLY operational observations, never real collection or model evidence.
afterEach(() => vi.unstubAllGlobals())
function mount(data: Record<string, unknown>, status = 200) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(status === 200 ? {
    data, source: 'TEST_ONLY', version: 'TEST_ONLY', as_of_session: null, artifact_id: null,
    classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null,
      research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' },
    provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null,
  } : { error_code: 'TEST_ONLY_UNAVAILABLE', message: 'TEST_ONLY monitoring unavailable', request_id: 'TEST_ONLY' }), { status }))
  vi.stubGlobal('fetch', fetch)
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><CollectionHealth /></QueryClientProvider>)
  return fetch
}

it('keeps an unpublished snapshot unavailable even when the alert list is empty', async () => {
  const fetch = mount({ local_alerts: { alerts: [], total: 0 }, provider_requests: 0 })
  expect(await screen.findByText(/No collection-monitoring snapshot has been published/)).toBeInTheDocument()
  expect(screen.queryByText('Verified fresh for saved expected session')).not.toBeInTheDocument()
  expect(fetch.mock.calls[0][0]).toBe('/api/v1/nse-market/collection-health')
})

it('shows partial stale evidence and recorded alert lifecycle without authorizing collection', async () => {
  mount({ read_at: '2000-01-03T15:00:00Z', snapshot_stale: true, expected_trading_session: '2000-01-03',
    coverage_session: '2000-01-03', accepted_securities: 2, configured_securities: 3, missing_securities: 1,
    quota: { reserved_requests_remaining: 0, run_slots_remaining: 0 }, forecast_freshness: { fresh_for_expected_session: false },
    local_alerts: { total: 1, alerts: [{ id: 'TEST_ONLY', title: 'TEST_ONLY worker failure', created_at: '2000-01-03T15:00:00Z', lifecycle: 'NEW', evidence: { reasons: ['TEST_ONLY_CLOCK_FAILURE'] } }] } })
  expect(await screen.findByText('2 / 3')).toBeInTheDocument()
  expect(screen.getByText(/monitoring snapshot is stale/)).toBeInTheDocument()
  expect(screen.getByText(/Unused capacity does not authorize another collecting slot/)).toBeInTheDocument()
  expect(screen.getByText('Unverified or stale')).toBeInTheDocument()
  expect(screen.getByRole('table', { name: 'Local collection alerts' })).toHaveTextContent('New')
  const scrollableAlerts = screen.getByRole('region', { name: 'Scrollable local collection alerts' })
  scrollableAlerts.focus()
  expect(scrollableAlerts).toHaveFocus()
  expect(scrollableAlerts).toContainElement(screen.getByRole('table', { name: 'Local collection alerts' }))
  expect(screen.getByText(/older conditions may have cleared/i)).toBeInTheDocument()
})

it('reports unavailable monitoring instead of filling missing counters', async () => {
  mount({}, 503)
  expect(await screen.findByText('Evidence unavailable')).toBeInTheDocument()
  expect(screen.queryByText('Accepted / configured securities')).not.toBeInTheDocument()
})

it('keeps unknown session eligibility separate from raw coverage and experimental outcomes', async () => {
  mount({ operational_readiness: { observed_at: '2000-01-03T15:00:00Z', snapshot_stale: true,
    qualification_stale: true, coverage: { historical_session_eligible_securities: null },
    forecasts: { raw_forecast_records: 3, unique_decisions: 2, matured_outcomes: 0, measurement_status: 'NOT_YET_MEASURABLE' },
    model_acceptance: { accepted_models: 0 }, collector_runtime: { active_dependency_advisories: 1,
      candidate_dependency_advisories: 0, cutover_status: 'BLOCKED_APPROVAL' } } })
  const panel = await screen.findByRole('region', { name: 'Unified operational readiness' })
  expect(panel).toHaveTextContent('NOT_YET_MEASURABLE')
  expect(panel).toHaveTextContent('historical tradability')
  expect(panel).toHaveTextContent('Not observed')
  expect(panel).toHaveTextContent('3 / 2')
  expect(panel).toHaveTextContent('BLOCKED_APPROVAL')
  expect(panel).toHaveTextContent('Runtime and security qualification needs rechecking')
})
