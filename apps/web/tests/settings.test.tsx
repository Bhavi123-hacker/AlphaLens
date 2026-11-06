import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Opportunities, Settings } from '../src/pages/Status'

vi.mock('../src/components/ProviderReadiness', () => ({ ProviderReadiness: () => null }))
vi.mock('../src/auth/Authentication', () => ({ AccountSettings: () => null }))
vi.mock('../src/components/Notifications', () => ({ NotificationPreferences: () => null, RecentAlerts: () => null }))

it('routes model and collector claims to measured saved evidence instead of asserting runtime state', () => {
  render(<MemoryRouter><Settings /></MemoryRouter>)
  expect(screen.getByRole('link', { name: 'Inspect saved predictions and model eligibility' })).toHaveAttribute('href', '/nse-market')
  expect(screen.getByRole('link', { name: 'inspect actual collection receipts and freshness' })).toHaveAttribute('href', '/nse-market')
  expect(screen.queryByText('Disabled', { exact: true })).not.toBeInTheDocument()
  expect(screen.queryByText(/scheduling disabled/i)).not.toBeInTheDocument()
  expect(screen.getByText(/This page refreshes saved diagnostic reads only/)).toBeInTheDocument()
})


it('separates unavailable accepted signals from genuine dated experimental predictions', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { enabled: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><Opportunities /></MemoryRouter></QueryClientProvider>)
  expect(screen.getByText('Current-session opportunities are unavailable')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Review dated experimental predictions' })).toHaveAttribute('href', '/nse-market')
  expect(screen.getByText(/fresh eligible observations and independent model acceptance are required/)).toBeInTheDocument()
  expect(screen.queryByText(/P19 source activation and experimental inference remain blocked/)).not.toBeInTheDocument()
})
