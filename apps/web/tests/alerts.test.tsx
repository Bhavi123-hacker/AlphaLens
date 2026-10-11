import { afterEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { NotificationBell, NotificationPreferences, Notifications } from '../src/components/Notifications'
import { alertSchema, preferenceSchema } from '../src/api/alerts'

const alert = { id: 'a'.repeat(64), category: 'DATA_SOURCE', severity: 'WARNING', title: 'TEST_ONLY source blocked', message: 'TEST_ONLY evidence does not support acquisition.', lifecycle: 'NEW', delivery: 'DELIVERED', evidence_status: 'TEST_ONLY', created_at: '2026-10-11T12:00:00Z', attempts: 1, next_attempt: null, delivered_at: '2026-10-11T12:00:00Z', delivery_reason: null, deduplication_key: 'b'.repeat(64), channel: 'IN_APP', external_delivery: 'NOT_REQUESTED', evidence: { code: 'SOURCE_BLOCKED', component: 'P19', evidence_ref: 'TEST_ONLY_RECEIPT', evidence_sha256: 'c'.repeat(64), event_at: '2026-10-11T12:00:00Z', time_basis: 'PERSISTED_EVENT_TIME', run_id: 'd'.repeat(64), security_id: null, session: '2026-10-09', classification: 'TEST_ONLY', final_vintage: null, mode: 'TEST_ONLY', reasons: ['TEST_ONLY_SOURCE_BLOCKER'] } }
const preferences = { version: 'p20.preferences.v1', categories: ['DATA_SOURCE', 'PIPELINE', 'ML_RESEARCH', 'PORTFOLIO', 'PAPER_TRADING'], include_info: false, quiet_enabled: false, quiet_start: '22:00', quiet_end: '07:00', timezone: 'Asia/Kolkata', cooldown_seconds: 3600, maximum_attempts: 3, retention_days: 90, email: false, desktop: false }
function response(data: unknown, page: unknown = null) { return new Response(JSON.stringify({ data, source: 'TEST_ONLY', version: 'p20.api.v1', as_of_session: null, artifact_id: null, classification: { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }, provenance: {}, evidence_status: 'TEST_ONLY', quality_status: 'TEST_ONLY', missing_data_reasons: [], page })) }
function wrapper(component: React.ReactNode) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{component}</MemoryRouter></QueryClientProvider>) }
function mock(enabled = false) {
  const fetcher = vi.fn().mockImplementation(async (url: string) => url.includes('unread-count') ? response({ count: 1 }) : url.includes('preferences') ? response({ preferences, mutations_enabled: enabled, channels: { IN_APP: 'AVAILABLE', EMAIL: 'UNAVAILABLE_NO_AUTHORIZED_SMTP', DESKTOP: 'UNAVAILABLE_NOT_DELIVERY_TESTED' }, stock_alerts: 'DISABLED_EVIDENCE_GATES_UNMET', scheduling: 'DISABLED' }) : response([alert], { limit: 20, offset: 0, total: 1, has_more: false }))
  vi.stubGlobal('fetch', fetcher); return fetcher
}
afterEach(() => vi.unstubAllGlobals())
it('shows unread count, verified history and disabled stock signal foundation', async () => {
  mock(); wrapper(<Notifications />)
  expect(await screen.findByText(alert.title)).toBeInTheDocument()
  expect(await screen.findByText('1')).toBeInTheDocument()
  expect(screen.getByText(/Stock alerts remain disabled/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /buy|sell|execute/i })).not.toBeInTheDocument()
})
it('filters by severity, search and delivery with bounded pagination', async () => {
  const fetcher = mock(); wrapper(<Notifications />); const user = userEvent.setup()
  await screen.findByText(alert.title)
  await user.selectOptions(screen.getByLabelText('Severity'), 'ERROR')
  await user.selectOptions(screen.getByLabelText('Delivery'), 'FAILED')
  await user.type(screen.getByLabelText('Search alerts'), 'TEST_ONLY')
  await waitFor(() => expect(fetcher.mock.calls.some(([url]) => String(url).includes('severity=ERROR') && String(url).includes('delivery=FAILED') && String(url).includes('search=TEST_ONLY'))).toBe(true))
  expect(screen.getByRole('button', { name: /Next/ })).toBeDisabled()
})
it('notification bell shows available count without external delivery', async () => {
  mock(); wrapper(<NotificationBell />)
  expect(await screen.findByRole('button', { name: 'Notifications, 1 unread' })).toBeInTheDocument()
})
it('preferences are explicitly unavailable when local mutations are off', async () => {
  mock(); wrapper(<NotificationPreferences />)
  expect(await screen.findByRole('button', { name: 'Save notification preferences' })).toBeDisabled()
  expect(screen.getByText(/Local mutation is disabled/)).toBeInTheDocument()
})
it('enabled preferences send the guarded JSON update and retain disabled channels', async () => {
  const fetcher = mock(true); wrapper(<NotificationPreferences />); const user = userEvent.setup()
  await user.click(await screen.findByLabelText('Deliver informational successes'))
  await user.click(screen.getByRole('button', { name: 'Save notification preferences' }))
  await screen.findByText(/Notification preferences saved/)
  const write = fetcher.mock.calls.find(([, options]) => options?.method === 'POST')
  expect(write?.[1].headers['X-AlphaLens-Local']).toBe('p20')
  expect(JSON.parse(write?.[1].body ?? '{}')).toEqual(expect.objectContaining({ include_info: true, email: false, desktop: false }))
})
it('contracts reject unsupported external channel activation and invalid delivery state', () => {
  expect(preferenceSchema.safeParse({ ...preferences, email: true }).success).toBe(false)
  expect(alertSchema.safeParse({ ...alert, delivery: 'READ' }).success).toBe(false)
})
it('unavailable backend does not produce notification fixtures', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('TEST_ONLY offline'))); wrapper(<Notifications />)
  expect(await screen.findByText(/local backend is disconnected/)).toBeInTheDocument()
  expect(screen.queryByText(alert.title)).not.toBeInTheDocument()
})
