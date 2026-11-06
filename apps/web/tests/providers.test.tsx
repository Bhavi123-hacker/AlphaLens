import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ProviderComparison } from '../src/components/ProviderComparison'
import { providerComparisonSchema } from '../src/api/providers'
import fixture from './fixtures/providers.json'

// Explicit TEST_ONLY documentation fixture, no synthetic prices or HTTP acquisition.
vi.mock('../src/api/client', () => ({ get: vi.fn(async () => ({ data: fixture, source: 'TEST_ONLY_PROVIDER_DOCS', classification: { usage_classification: 'TEST_ONLY' }, missing_data_reasons: [], provenance: {} })) }))
function view() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><ProviderComparison /></QueryClientProvider>) }
describe('provider comparison evidence and controls', () => {
  it('shows all six blocked candidates and distinguishes archive from acquired sessions', async () => {
    view()
    expect(await screen.findByRole('article', { name: 'Upstox readiness' })).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(6)
    expect(screen.getByText('Original accepted-model inference remains gated')).toBeInTheDocument()
    expect(screen.getAllByText('None acquired')).toHaveLength(6)
    expect(screen.queryByRole('button', { name: /activate|download/i })).not.toBeInTheDocument()
  })
  it('filter and capacity selectors change only presentation', async () => {
    view(); await screen.findByRole('article', { name: 'Upstox readiness' })
    await userEvent.selectOptions(screen.getByLabelText('Compare provider'), 'upstox')
    await userEvent.selectOptions(screen.getByLabelText('Provider capacity scenario'), '500')
    expect(screen.getAllByRole('article')).toHaveLength(1)
    expect(screen.getByText('500', { exact: true })).toBeInTheDocument()
    expect(screen.getByText(/not measured performance/)).toBeInTheDocument()
    expect(screen.getByText('UNDER REVIEW')).toBeInTheDocument()
  })
  it('typed client rejects enabled acquisition, unknown remaining quota is nullable', () => {
    expect(providerComparisonSchema.safeParse(fixture).success).toBe(true)
    expect(providerComparisonSchema.safeParse({ ...fixture, collection_enabled: true }).success).toBe(false)
    expect(providerComparisonSchema.parse(fixture).providers.every(p => p.provider_remaining_daily_allowance === null)).toBe(true)
  })
})
