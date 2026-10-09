import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '../src/App'
import { navigation } from '../src/lib/navigation'
import { ErrorState, StockSearch } from '../src/components/ui'
import { APIError } from '../src/api/client'
import { Paper, Portfolios } from '../src/pages/Accounts'
import { Opportunities } from '../src/pages/Status'

// All constructed responses in this suite are TEST_ONLY; none are runtime fallbacks.
function wrapper(children: React.ReactNode, path = '/') {
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={query}><MemoryRouter initialEntries={[path]}>{children}</MemoryRouter></QueryClientProvider>)
}
function unavailable() {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(JSON.stringify({ error_code: 'DATABASE_NOT_CONFIGURED', message: 'TEST_ONLY: database not configured.' }), { status: 503 })))
}
function fixtureResponse(data: unknown) { return new Response(JSON.stringify({ data, source: 'TEST_ONLY_API_FIXTURE', as_of_session: null,
  classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null,
    p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, version: 'TEST_ONLY', artifact_id: null,
  provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null })) }
afterEach(() => vi.unstubAllGlobals())
describe('application evidence and interaction', () => {
  it('provides ten distinct working navigation destinations', () => {
    expect(navigation).toHaveLength(10); expect(new Set(navigation.map(([path]) => path)).size).toBe(10)
  })
  it('renders 503 as unavailable with traced machine-readable reasons', () => {
    wrapper(<ErrorState error={new APIError(503, 'EVIDENCE_UNAVAILABLE', 'TEST_ONLY unavailable', ['MODEL_EVIDENCE_UNAVAILABLE'])} />)
    expect(screen.getByText('Evidence unavailable')).toBeInTheDocument(); expect(screen.getByText('Model evidence unavailable')).toBeInTheDocument()
  })
  it('portfolio workspace preserves unavailable database state without holdings', async () => {
    unavailable(); wrapper(<Portfolios />); expect(await screen.findByText('TEST_ONLY: database not configured.')).toBeInTheDocument(); expect(screen.queryByText('₹100,000')).not.toBeInTheDocument()
  })
  it('paper workspace is explicitly simulated and has no execution form', async () => {
    unavailable(); wrapper(<Paper />); expect(await screen.findByText('TEST_ONLY: database not configured.')).toBeInTheDocument(); expect(screen.getByText('Simulation only · read-only workspace')).toBeInTheDocument(); expect(screen.queryByRole('button', { name: /place order|buy|sell/i })).not.toBeInTheDocument()
  })
  it.each([[false, 'No portfolio records'], [true, 'No paper accounts recorded']] as const)('shows an honest connected empty workspace (paper=%s)', async (paper, title) => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => fixtureResponse([]))); wrapper(paper ? <Paper /> : <Portfolios />)
    expect(await screen.findByText(title)).toBeInTheDocument(); expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
  it('renders recorded FIFO basis while unavailable market valuations stay unavailable', async () => {
    const account = { portfolio_id: 'TEST_ONLY:PORTFOLIO', portfolio_name: 'TEST_ONLY constructed ledger', portfolio_type: 'USER_RECORDED',
      base_currency: 'INR', classification: 'USER_RECORDED', created_at: '2020-01-01T00:00:00Z', accounting_policy: { version: 'p15.accounting.v1', method: 'FIFO' } }
    const position = { security_id: 'TEST_ONLY:SECURITY', transaction_symbol: 'TEST_ONLY', quantity: '2', cost_basis: '201', realized_pnl: '0', fees: '1', lots: [{ transaction_id: 'TEST_ONLY:BUY', session: '2020-01-01', quantity: '2', cost_basis: '201', provenance: 'USER_RECORDED' }] }
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string) => fixtureResponse(url.includes('/holdings?') ? { positions: [position], market_value: null, unrealized_pnl: null, valuation_status: 'UNAVAILABLE', risk_status: 'UNAVAILABLE', signal_status: 'UNAVAILABLE' }
      : url.includes('/performance?') ? { accounting: { cash: '799', positions: [position], ledger_state_id: 'TEST_ONLY' }, portfolio_value: null, unrealized_pnl: null, total_pnl: null, session_pnl: null, performance_history: null, valuation_status: 'UNAVAILABLE' }
        : url.includes('/portfolios?') ? [account] : account)))
    wrapper(<Portfolios />); expect(await screen.findByRole('cell', { name: '201' })).toBeInTheDocument()
    expect(await screen.findByText('799', { exact: true })).toBeInTheDocument(); expect(screen.getAllByText('Unavailable', { exact: true }).length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByTestId('financial-chart')).not.toBeInTheDocument()
  })
  it('current opportunities remain unavailable and state definitions are reference material', async () => {
    unavailable(); wrapper(<Opportunities />); expect(screen.getByText('Current-session opportunities are unavailable')).toBeInTheDocument(); expect(screen.getByText('Definitions only — these are not active signals')).toBeInTheDocument(); await waitFor(() => expect(screen.getAllByText('Evidence unavailable')).toHaveLength(3))
  })
  it('settings route and application shell preserve the research restriction', async () => {
    unavailable(); wrapper(<App />, '/settings'); expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument(); expect(screen.getByText('Research only')).toBeInTheDocument(); expect(screen.getByText('Final-vintage archive · not production-cleared')).toBeInTheDocument(); expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main-content')
  })
  it('debounces symbol search and supports keyboard identity selection', async () => {
    const select = vi.fn(); const mock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ data: [{ security_id: 'TEST_ONLY:isin:ONE', first_observed: '2020-01-01', last_observed: '2020-01-02', observation_count: 2, latest_observed_symbol: 'TEST_ONLY', latest_observed_name: 'Constructed test identity' }], source: 'TEST_ONLY', as_of_session: null, classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, version: 'TEST_ONLY', artifact_id: null, provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null })))
    vi.stubGlobal('fetch', mock); wrapper(<StockSearch onSelect={select} />); const user = userEvent.setup(); const input = screen.getByRole('combobox'); await user.type(input, 'TEST')
    await waitFor(() => expect(mock.mock.calls.some((args: unknown[]) => String(args[0]).includes('q=TEST'))).toBe(true))
    await user.keyboard('{ArrowDown}{Enter}'); expect(select).toHaveBeenCalledWith(expect.objectContaining({ security_id: 'TEST_ONLY:isin:ONE' }))
  })
  it('keeps securities distinct when they share a ticker', async () => {
    const select = vi.fn(); vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => fixtureResponse(['ONE', 'TWO'].map((id) => ({ security_id: 'TEST_ONLY:isin:' + id, latest_observed_symbol: 'SAME_TEST_ONLY', latest_observed_isin: 'TEST_ONLY_' + id, latest_observed_name: 'Constructed identity ' + id, first_observed: '2020-01-01', last_observed: '2020-01-02', observation_count: 2 })))))
    wrapper(<StockSearch onSelect={select} />); const user = userEvent.setup(); await user.click(screen.getByRole('combobox'))
    await waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(2)); expect(screen.getByText('TEST_ONLY_ONE')).toBeInTheDocument(); expect(screen.getByText('TEST_ONLY_TWO')).toBeInTheDocument()
    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}'); expect(select).toHaveBeenCalledWith(expect.objectContaining({ security_id: 'TEST_ONLY:isin:TWO' }))
  })
})
