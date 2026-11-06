import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ExperimentalResearch } from '../src/pages/Experimental'
import { experimentalWorkspaceSchema } from '../src/api/experimental'

// TEST_ONLY contract examples; these are never runtime market or model evidence.
function workspace(count = 6) {
  return { schema: 'alphalens.experimental_nse.workspace.v1', family: 'ALPHALENS_EXPERIMENTAL_NSE_V1', status: 'EXPERIMENTAL_UNVALIDATED_RESEARCH', label: 'EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED', available: true, model: { id: 'TEST_ONLY_MODEL', algorithm: 'TEST_ONLY logistic', feature_version: 'TEST_ONLY', horizon: '5 observed sessions' }, dataset: { id: 'TEST_ONLY_DATA', securities: count, observations: 100, start: '2025-01-01', end: '2025-12-01', source: 'TEST_ONLY', price_basis: 'TEST_ONLY' }, evaluation: { metrics: { balanced_accuracy: 0.5 }, limitations: ['TEST_ONLY_NOT_PERFORMANCE'] }, candidates: Array.from({ length: count }, (_, i) => ({ key: 'NSE_EQ|INE' + String(i).padStart(9, '0'), symbol: 'TEST_ONLY_' + i, score: 0.7 - i / 100, observation_date: '2025-12-01', source: 'TEST_ONLY', volatility_percent: null, drawdown_percent: null, held: i === 0, preferences: { state: i === 0 ? 'MATCHES_SUPPORTED_CONSTRAINTS' : 'INSUFFICIENT_EVIDENCE', matched: ['minimum_volume'], excluded: [], missing: i === 0 ? [] : ['maximum_drawdown_percent'], unsupported: ['RISK_TOLERANCE_CATEGORY_CALIBRATION'] }, missing_evidence: ['INDEPENDENT_ACCEPTANCE'], exclusions: [] })), exclusions: [], prospective: { forecasts: count, outcomes: 0, metrics: null, status: 'AWAITING_FUTURE_OBSERVATIONS' }, accepted_current_rankings: 0 }
}
function response(data: unknown) {
  return new Response(JSON.stringify({ data, source: 'TEST_ONLY', version: 'TEST_ONLY', as_of_session: null, artifact_id: null, classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null }))
}
function mount(data: unknown) {
  const fetch = vi.fn().mockResolvedValue(response(data))
  vi.stubGlobal('fetch', fetch)
  render(<MemoryRouter><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><ExperimentalResearch /></QueryClientProvider></MemoryRouter>)
  return fetch
}
afterEach(() => vi.unstubAllGlobals())
it('renders saved actual scores and identity-aligned chart links without filling missing Top 20 rows', async () => {
  const fetch = mount(workspace())
  expect(await screen.findByText('TEST_ONLY_0')).toBeInTheDocument()
  expect(screen.getByText('0.700000')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'TEST_ONLY_0' })).toHaveAttribute('href', '/stocks/' + encodeURIComponent('upstox:NSE_EQ|INE000000000'))
  await userEvent.selectOptions(screen.getByLabelText('Experimental research list size'), '20')
  const table = within(screen.getByRole('region', { name: 'Experimental model research candidates' })).getByRole('table')
  expect(within(table).getAllByTestId('experimental-score')).toHaveLength(6)
  expect(screen.getByText(/6 displayed \/ 6 eligible in this view \/ 6 genuinely scored/)).toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(fetch.mock.calls[0][0]).toBe('/api/v1/experimental-nse/research')
  expect(screen.getByText('EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED')).toBeInTheDocument()
  expect(screen.getByText(/No matured prospective evidence exists yet/)).toBeInTheDocument()
})
it('filters only supported preference matches without changing model order or manufacturing confidence', async () => {
  mount(workspace())
  await screen.findByText('TEST_ONLY_0')
  await userEvent.click(screen.getByLabelText('Only matches to supported preferences'))
  expect(screen.getAllByTestId('experimental-score')).toHaveLength(1)
  expect(screen.getByText(/Already held: review concentration/)).toBeInTheDocument()
  expect(screen.queryByText('TEST_ONLY_1')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /buy|sell|train|execute/i })).not.toBeInTheDocument()
})
it('keeps missing experimental evidence empty and accepted rankings zero', async () => {
  mount({ ...workspace(0), available: false, model: null, dataset: null, evaluation: null })
  expect(await screen.findByText('No eligible experimental model output has been saved')).toBeInTheDocument()
  expect(screen.queryByTestId('experimental-score')).not.toBeInTheDocument()
  expect(experimentalWorkspaceSchema.safeParse({ ...workspace(), accepted_current_rankings: 1 }).success).toBe(false)
  expect(experimentalWorkspaceSchema.safeParse({ ...workspace(), family: 'FROZEN_CANDIDATE' }).success).toBe(false)
  const malformed = workspace(); malformed.candidates[0].score = Number.NaN
  expect(experimentalWorkspaceSchema.safeParse(malformed).success).toBe(false)
})
it('shows failed baseline comparison prominently instead of implying a predictive edge', async () => {
  mount({ ...workspace(), evaluation: { final_beats_both_baselines_on_balanced_accuracy: false, final: { candidate: { balanced_accuracy: 0.48, sample_count: 50, date_count: 10, start: '2025-01-01', end: '2025-01-14' }, baseline_train_majority: { balanced_accuracy: 0.5 }, baseline_trailing5_open_close_direction: { balanced_accuracy: 0.51 } } } })
  expect(await screen.findByText('No demonstrated predictive edge')).toBeInTheDocument()
  expect(screen.getByText(/This model did not outperform the predeclared baselines/)).toBeInTheDocument()
  expect(screen.getByText('0.4800')).toBeInTheDocument()
})
