import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { SavedMarket, SavedStock } from '../src/components/SavedMarket'
import { StockWorkspace } from '../src/components/StockWorkspace'

vi.mock('../src/components/Chart', () => ({ Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} /> }))
// TEST_ONLY display contracts, never a real security or performance claim.
const row = { key: 'NSE_EQ|INE000000000', symbol: 'TEST_ONLY', name: 'TEST_ONLY company',
  session: '2026-10-21', freshness: 'DATED_COMPLETED_SESSION', previous_close: null,
  change: null, change_percent: null, received_at: '2026-10-22T10:00:00Z', source: 'TEST_ONLY',
  open: '100', high: '110', low: '90', close: '105', volume: 123 }
const meta = { mode: 'SAVED_COMPLETED_SESSION_NOT_LIVE', latest_observed_session: '2026-10-21',
  as_of: '2026-10-24T10:00:00Z', price_basis: 'TEST_ONLY', provider_requests: 0,
  configured_securities: 500, latest_session_securities: 248 }
function mount(component: React.ReactNode, observed: Record<string,unknown> = row, historyRows: Record<string,unknown>[] = [row]) {
  const fetch = vi.fn().mockImplementation((path: string) => Promise.resolve(new Response(JSON.stringify({
    data: path.includes('saved-history') ? { ...meta, security: observed, rows: historyRows } : { ...meta, total: 1, rows: [observed] },
    source: 'TEST_ONLY', version: 'TEST_ONLY', as_of_session: null, artifact_id: null,
    classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null,
      research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' },
    provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null,
  }))))
  vi.stubGlobal('fetch', fetch)
  render(<MemoryRouter><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{component}</QueryClientProvider></MemoryRouter>)
  return fetch
}
afterEach(() => vi.unstubAllGlobals())
it('uses saved search and leader endpoints while preserving missing changes', async () => {
  const fetch = mount(<SavedMarket />)
  expect(await screen.findByText('TEST_ONLY company')).toBeInTheDocument()
  expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
  expect(screen.queryByText('0.00%')).not.toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Saved market view'), 'gainers')
  await waitFor(() => expect(fetch.mock.calls.some(([path]) => String(path).includes('order=gainers'))).toBe(true))
  await userEvent.type(screen.getByLabelText('Search saved NSE prices'), 'TEST')
  await waitFor(() => expect(fetch.mock.calls.some(([path]) => String(path).includes('q=TEST'))).toBe(true))
  expect(fetch.mock.calls.every(([path]) => String(path).startsWith('/api/v1/nse-market/saved-market?'))).toBe(true)
})

it('opens a supported master-only stock without inventing price, history or forecast', async () => {
  const noHistory = { ...row, name: 'TEST_ONLY no history', session: null, freshness: 'UNAVAILABLE',
    open: null, high: null, low: null, close: null, volume: null, received_at: null,
    support_status:'SUPPORTED_EQUITY_NO_SAVED_HISTORY', ml_status:'NO_COMPATIBLE_SAVED_PREDICTION',
    identity_status:{state:'STALE'} }
  const fetch = mount(<SavedStock instrumentKey={row.key} />, noHistory, [])
  expect(await screen.findByText('No saved candles for this identity')).toBeInTheDocument()
  expect(screen.getByText(/Supported Equity No Saved History/i)).toBeInTheDocument()
  expect(screen.getByText(/No Compatible Saved Prediction/i)).toBeInTheDocument()
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
  expect(screen.getByText(/current listing and provider access are unverified/)).toBeInTheDocument()
  expect(fetch.mock.calls.every(([path])=>String(path).startsWith('/api/v1/nse-market/saved-history?'))).toBe(true)
})
it('opens selected stock saved candles without invoking provider transports', async () => {
  const fetch = mount(<StockWorkspace securityId="upstox:NSE_EQ|INE000000000" />)
  expect(await screen.findByRole('img', { name: 'Saved TEST_ONLY daily price and volume' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Saved daily observations' })).toHaveAttribute('aria-pressed', 'true')
  expect(fetch.mock.calls.every(([path]) => String(path).startsWith('/api/v1/nse-market/saved-history?'))).toBe(true)
  expect(screen.getByText(/NOT A LIVE QUOTE/)).toBeInTheDocument()
})
