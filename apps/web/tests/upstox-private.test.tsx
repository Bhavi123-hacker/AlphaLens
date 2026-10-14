import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UpstoxPrivateView } from '../src/components/UpstoxPrivateView'
import { get } from '../src/api/client'

vi.mock('../src/api/client', () => ({ get: vi.fn(async () => ({ data: { state: 'AUTH_REJECTED', rows: [], indicators: {}, retained: false } })) }))
function view() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><UpstoxPrivateView /></QueryClientProvider>) }
describe('explicit bounded private provider view', () => {
  it('makes no provider request until the operator selects the private view', () => {
    vi.mocked(get).mockClear(); view()
    expect(get).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Load private RELIANCE candles' })).toBeInTheDocument()
    expect(screen.getByText(/No retained ingestion or ML prediction follows/)).toBeInTheDocument()
  })
  it('displays authentication rejection without archive or fixture fallback', async () => {
    vi.mocked(get).mockClear(); view()
    await userEvent.click(screen.getByRole('button', { name: 'Load private RELIANCE candles' }))
    expect(await screen.findByText('AUTH_REJECTED')).toBeInTheDocument()
    expect(get).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})
