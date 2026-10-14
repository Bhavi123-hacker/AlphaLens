import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProviderChart, ProviderWorkspace } from '../src/components/ProviderWorkspace'
import { StockWorkspace } from '../src/components/StockWorkspace'
import { currency } from '../src/lib/format'
import { priceTooltip } from '../src/lib/chart-options'
import type { ProviderSnapshot } from '../src/api/terminal'

vi.mock('../src/components/Chart', () => ({ Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} /> }))
// TEST_ONLY constructed provider contract; never imported by runtime pages.
const item: ProviderSnapshot = {
  state: 'AVAILABLE_PRIVATE_TRANSIENT', identity: { symbol: 'TEST_ONLY_EQ', name: 'TEST_ONLY equity', provider_key: 'NSE_EQ|INE000000001', isin: 'INE000000001', exchange: 'NSE', segment: 'NSE_EQ', instrument_type: 'EQ', observed_at: '2026-10-14T16:00:00Z', revision_sha256: 'a'.repeat(64) },
  instrument_key: 'NSE_EQ|INE000000001', symbol: 'TEST_ONLY_EQ', source: 'TEST_ONLY', price_basis: 'UNKNOWN', retained: false, streaming: false, received_at: '2026-10-14T16:00:00Z', cache_age_seconds: 0, cache_ttl_seconds: 600,
  latest_session: '2026-10-13', latest_close: '100.125', change: '1.125', change_percent: '1.13', current_session_status: 'MARKET_CLOSED_EOD_CANDLE_PENDING', official_final_close: 'NOT_INDEPENDENTLY_ESTABLISHED',
  market: { state: 'CLOSED', session: '2026-10-14' }, quote: { state: 'VALIDATED_SNAPSHOT', ltp: '105.9252499999999', previous_close: '100.125', change: '5.8002499999999', change_percent: '5.79', snapshot_at: '2026-10-14T16:00:00Z', last_trade_at: '2026-10-14T10:00:00Z', freshness: 'SAME_LOCAL_DATE_TRADE', clock: { local_received_at: '2026-10-14T16:00:00Z', https_server_date: null, server_minus_local_seconds: null, validation: 'NO_FUTURE_TIMESTAMP_TOLERANCE' } },
  session_ohlc: { state: 'VALIDATED_PROVIDER_OHLC', current: null, previous: null }, rows: [{ session: '2026-10-13', open: '99', high: '105', low: '97', close: '100.125', volume: 100 }], indicators: {},
  passport: { identity_source: 'TEST_ONLY', master_revision: 'a'.repeat(64), retrieval_time: '2026-10-14T16:00:00Z', publication_time: null, historical_archive_joined: false, current_inference: 'UNAVAILABLE', blockers: ['TEST_ONLY_MODEL_NOT_ACCEPTED'] },
}
function view(node: React.ReactNode) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{node}</MemoryRouter></QueryClientProvider>) }
function envelope(data: unknown) { return new Response(JSON.stringify({ data, source: 'TEST_ONLY', as_of_session: null, classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, version: 'TEST_ONLY', artifact_id: null, provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY', missing_data_reasons: [], page: null })) }
afterEach(() => vi.unstubAllGlobals())
describe('current-price terminal semantics', () => {
  it('rounds display currency with exact integer arithmetic, preserving stored text', () => {
    expect(currency('978.9252499999999')).toBe('978.93'); expect(currency('999.995')).toBe('1,000.00'); expect(currency('-0.005')).toBe('-0.01'); expect(currency('0')).toBe('0.00'); expect(currency(null)).toBe('Unavailable'); expect(item.latest_close).toBe('100.125')
  })
  it('cleans currency tooltips and preserves volume integer formatting', () => {
    const text = priceTooltip([{ axisValueLabel: 'TEST_ONLY_DATE', seriesName: 'SMA', data: 978.9252499999999 }, { seriesName: 'Volume', data: 1000 }])
    expect(text).toContain('978.93'); expect(text).toContain('1,000'); expect(text).not.toContain('92524999')
    expect(priceTooltip([{ seriesType: 'candlestick', data: [100.123456, 101.25, 99, 105] }])).toContain('O 100.12  H 105.00  L 99.00  C 101.25')
  })
  it('keeps LTP, provider daily close and pending release distinct', () => {
    view(<ProviderChart data={item} />)
    expect(screen.getByText('₹105.93')).toBeInTheDocument(); expect(screen.getByText('Last traded price · quote snapshot')).toBeInTheDocument(); expect(screen.getByText('Provider EOD close · 2026-10-13')).toBeInTheDocument(); expect(screen.getByText('Market closed eod candle pending')).toBeInTheDocument(); expect(screen.getAllByText('₹100.13')).toHaveLength(2)
  })
  it('rejected current quote uses explicitly labeled EOD and never presents LTP', () => {
    view(<ProviderChart data={{ ...item, quote: { ...item.quote, state: 'QUOTE_TIME_REJECTED', ltp: undefined, previous_close: undefined } }} />)
    expect(screen.getByText('Latest provider EOD candle close')).toBeInTheDocument(); expect(screen.getByText(/Current quote: Quote time rejected/)).toBeInTheDocument(); expect(screen.queryByText('₹105.93')).not.toBeInTheDocument()
  })
  it('makes no provider request until explicitly loaded, then puts selected candles in the chart', async () => {
    const fetch = vi.fn(async () => envelope({ state: 'SELECTED_PRIVATE_WATCHLIST', items: [item], queried_count: 1, full_nse_coverage: false, retained: false, api_calls_this_request: 0 })); vi.stubGlobal('fetch', fetch)
    view(<ProviderWorkspace instrumentKey={item.instrument_key} />)
    expect(fetch).not.toHaveBeenCalled(); await userEvent.click(screen.getByRole('button', { name: 'Load Upstox observations' }))
    expect(await screen.findByRole('img', { name: 'Upstox TEST_ONLY_EQ daily OHLCV ending 2026-10-13' })).toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('canonical workspace defaults to provider selection without reading archive history', async () => {
    const fetch = vi.fn(async () => envelope({ security_id: 'TEST_ONLY:one', first_observed: '2020-01-01', last_observed: '2026-10-06', observation_count: 100, observed_identity_evidence: [{ security_id: 'TEST_ONLY:one', symbol: 'TEST_ONLY_EQ', name: 'TEST_ONLY equity', isin: item.identity.isin, analytical_type: 'TEST_ONLY', identity_basis: 'TEST_ONLY', first_observed: '2020-01-01', last_observed: '2026-10-06' }], identity_semantics: 'TEST_ONLY', fundamental_pit_analysis: 'UNAVAILABLE', benchmark_status: 'UNAVAILABLE', price_basis: 'RAW_UNADJUSTED' })); vi.stubGlobal('fetch', fetch)
    view(<StockWorkspace securityId="TEST_ONLY:one" />)
    expect(await screen.findByRole('button', { name: 'Upstox · latest provider observations' })).toHaveAttribute('aria-pressed', 'true'); expect(fetch).toHaveBeenCalledTimes(1); expect(screen.queryByRole('img')).not.toBeInTheDocument(); expect(screen.getByRole('button', { name: 'AlphaLens Historical Archive · 2026-10-06' })).toBeInTheDocument()
  })
  it('expires provider prices in memory without an automatic second request', async () => {
    const fetch = vi.fn(async () => envelope({ state: 'SELECTED_PRIVATE_WATCHLIST', items: [{ ...item, cache_ttl_seconds: 0.05 }], queried_count: 1, full_nse_coverage: false, retained: false, api_calls_this_request: 0 })); vi.stubGlobal('fetch', fetch)
    view(<ProviderWorkspace instrumentKey={item.instrument_key} />)
    await userEvent.click(screen.getByRole('button', { name: 'Load Upstox observations' }))
    expect(await screen.findByRole('img')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Load Upstox observations' })).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1)
  })
})
