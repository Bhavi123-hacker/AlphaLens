import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ExperimentalResearchV2 } from '../src/pages/ExperimentalV2'
import { experimentalV2WorkspaceSchema } from '../src/api/experimental-v2'

// TEST_ONLY fixtures exercise rendering contracts, never actual research evidence.
function workspace(count = 6) {
  return { schema: 'alphalens.experimental_nse_v2.workspace.v1', family: 'ALPHALENS_EXPERIMENTAL_NSE_V2', status: 'PROSPECTIVE_EVALUATION_IN_PROGRESS', available: true, model: { id: 'TEST_ONLY_MODEL', algorithm: 'TEST_ONLY logistic', horizon: 'TEST_ONLY next eligible session', target_definition: 'TEST_ONLY target, not a five-session holding return', calibration_status: 'UNCALIBRATED_MODEL_SCORE', feature_version: 'TEST_ONLY_V2' }, dataset: { observations: 100, start: '2025-01-01', end: '2025-12-01', price_basis: 'TEST_ONLY_UNKNOWN', source: 'TEST_ONLY' }, evaluation: { edge_status: 'NO_DEMONSTRATED_EDGE', comparisons: [{ algorithm: 'TEST_ONLY candidate', metrics: { balanced_accuracy: 0.49, roc_auc: 0.5, brier_score: 0.26 } }, { algorithm: 'TEST_ONLY majority', metrics: { balanced_accuracy: 0.5 } }] }, candidates: Array.from({ length: count }, (_, i) => ({ key: 'NSE_EQ|INE' + String(i).padStart(9, '0'), symbol: 'TEST_ONLY_V2_' + i, score: 0.7 - i / 100, observation_date: '2025-12-01', source: 'TEST_ONLY', risk_kind: 'INTRADAY_ONLY', volatility_percent: null, drawdown_percent: null, preferences: { state: i === 0 ? 'MATCHES_SUPPORTED_CONSTRAINTS' : 'INSUFFICIENT_EVIDENCE', matched: [], excluded: [], missing: [], unsupported: [] }, held: i === 0 })), exclusions: ['TEST_ONLY_PRICE_BASIS_UNKNOWN'], prospective: { forecasts: count, outcomes: 0, eligible_forecasts: count, metrics: null, status: 'AWAITING_FUTURE_OBSERVATIONS' }, accepted_current_rankings: 0 }
}
function mount(data: unknown) {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data, source: 'TEST_ONLY', version: 'TEST_ONLY', as_of_session: null, artifact_id: null, classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null })))
  vi.stubGlobal('fetch', fetch)
  render(<MemoryRouter><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><ExperimentalResearchV2 /></QueryClientProvider></MemoryRouter>)
  return fetch
}
afterEach(() => vi.unstubAllGlobals())
it('shows dynamic target, failed edge, actual score order and only genuine coverage', async () => {
  const fetch = mount(workspace())
  expect(await screen.findByText('TEST_ONLY_V2_0')).toBeInTheDocument()
  expect(screen.getByText('0.700000')).toBeInTheDocument()
  expect(screen.getByText('Target: TEST_ONLY target, not a five-session holding return')).toBeInTheDocument()
  expect(screen.getByText('No demonstrated edge')).toBeInTheDocument()
  expect(screen.getByText('0.49000')).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('V2 research list size'), '20')
  expect(screen.getAllByTestId('v2-model-score')).toHaveLength(6)
  expect(screen.getByRole('link', { name: 'TEST_ONLY_V2_0' })).toHaveAttribute('href', '/stocks/' + encodeURIComponent('upstox:NSE_EQ|INE000000000'))
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][0]).toBe('/api/v1/experimental-nse-v2/research')
  expect(screen.getByText(/No matured V2 prospective outcomes exist yet/)).toBeInTheDocument()
})
it('applies supported preferences without replacing scores or manufacturing holdings', async () => {
  mount(workspace())
  await screen.findByText('TEST_ONLY_V2_0')
  await userEvent.click(screen.getByLabelText('Only V2 matches to supported preferences'))
  expect(screen.getAllByTestId('v2-model-score')).toHaveLength(1)
  expect(screen.getByText(/Already held: inspect dated portfolio concentration/)).toBeInTheDocument()
  expect(screen.queryByText('TEST_ONLY_V2_1')).not.toBeInTheDocument()
})
it('does not promote unreviewed experiments or fill missing scores', async () => {
  mount({ ...workspace(0), available: false, model: null, dataset: null, evaluation: null })
  expect(await screen.findByText('No eligible V2 scores in this view')).toBeInTheDocument()
  expect(screen.queryByTestId('v2-model-score')).not.toBeInTheDocument()
  expect(experimentalV2WorkspaceSchema.safeParse({ ...workspace(), accepted_current_rankings: 1 }).success).toBe(false)
  expect(experimentalV2WorkspaceSchema.safeParse({ ...workspace(), status: 'INDEPENDENTLY_ACCEPTED' }).success).toBe(false)
  expect(experimentalV2WorkspaceSchema.safeParse({ ...workspace(), family: 'ALPHALENS_EXPERIMENTAL_NSE_V1' }).success).toBe(false)
})
it('explains real identity, saved technical evidence, cost exposure and pending future sessions without invented performance', async () => {
  const base = workspace(1)
  const fetch = mount({ ...base, operations: { state: 'PUBLICATION_PENDING', message: 'TEST_ONLY waiting for publication', last_failure: { stage: 'collection', code: 'TEST_ONLY_PENDING', message: 'TEST_ONLY bounded source is pending', traceback: 'TEST_ONLY_TRACEBACK_MUST_NOT_RENDER' }, stages: [], source_requests_last_run: 0 }, candidates: base.candidates.map(row => ({ ...row, company_name: 'TEST_ONLY COMPANY', identity: { exchange: 'NSE', segment: 'NSE_EQ', instrument_type: 'EQ', isin: 'INE000000000' }, technical_evidence: [{ feature: 'price_return_5', label: 'TEST_ONLY observed return', value: 5, unit: 'percent' }], portfolio_context: [{ portfolio_name: 'TEST_ONLY manual portfolio', cost_allocation_percent: 100, concentration_review: true }] })), prospective: { ...base.prospective, lifecycle: { pending: 1, excluded: 0, missing: 0, unknown: 0, rejected: null }, pending_forecasts: [{ key: 'NSE_EQ|INE000000000', symbol: 'TEST_ONLY_V2_0', first_required_open_at: '2026-10-19T03:45:00+00:00', observed_sessions: 0, remaining_sessions: 5, reason: 'FUTURE_ENTRY_NOT_STARTED', missing_sessions: [] }] } })
  expect(await screen.findByText('TEST_ONLY COMPANY')).toBeInTheDocument()
  expect(screen.getByText('TEST_ONLY observed return: 5.000 percent')).toBeInTheDocument()
  expect(screen.getByText(/100.00% of remaining FIFO cost/)).toBeInTheDocument()
  expect(screen.getByText('Cost concentration is not market-value exposure.')).toBeInTheDocument()
  expect(screen.getByRole('table', { name: 'Outstanding genuine prospective evidence' })).toHaveTextContent('0 / 5')
  expect(screen.getByText('TEST_ONLY bounded source is pending')).toBeInTheDocument()
  expect(screen.queryByText('TEST_ONLY_TRACEBACK_MUST_NOT_RENDER')).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Historical and technical leaders/ })).toHaveAttribute('href', '/opportunities')
  expect(fetch).toHaveBeenCalledTimes(1)
})
