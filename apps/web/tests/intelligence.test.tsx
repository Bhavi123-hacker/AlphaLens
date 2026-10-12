import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EvidencePassport } from '../src/components/EvidencePassport'
import { Intelligence } from '../src/pages/Intelligence'
import { passportSchema, regimeSchema, reliabilitySchema } from '../src/api/intelligence'
import passport from './fixtures/p29-passport.json'
import regime from './fixtures/p29-regime.json'
import reliability from './fixtures/p29-reliability.json'

vi.mock('../src/components/Chart', () => ({ Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} /> }))
vi.mock('../src/api/client', () => ({ queryString: (values: Record<string, string | number>) => new URLSearchParams(Object.entries(values).map(([k, v]) => [k, String(v)])).toString(), get: vi.fn(async (path: string) => path.includes('/passport/') ? passport : path.includes('/reliability') ? reliability : regime) }))
function view(child: React.ReactNode) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{child}</QueryClientProvider>) }

it('TEST_ONLY passport shows recorded identity, missingness and real blocker layers', async () => {
  view(<EvidencePassport securityId="TEST_ONLY:STABLE_ID_A" />)
  expect(await screen.findByText('TESTISIN_A')).toBeInTheDocument()
  expect(screen.getByText('CURRENT SHORTLIST UNAVAILABLE')).toBeInTheDocument()
  expect(screen.queryByText(/confidence.*%/i)).not.toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Evidence blocker layer'), 'model')
  expect(screen.getByText(/Independent model acceptance not passed/i)).toBeInTheDocument()
  expect(screen.queryByText(/No approved ongoing nse provider/i)).not.toBeInTheDocument()
})

it('passport detail drawer explains artifact identities without inventing checksums', async () => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.removeAttribute('open') } })
  view(<EvidencePassport securityId="TEST_ONLY:STABLE_ID_A" />)
  await userEvent.click(await screen.findByRole('button', { name: 'Inspect passport details' }))
  expect(screen.getByRole('dialog', { name: 'Detailed Evidence Passport' })).toBeInTheDocument()
  expect(screen.getByText('Checksum not recorded')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Close details' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

it('intelligence tabs keep insufficient PIT evidence separate from archival description', async () => {
  view(<Intelligence />)
  expect(await screen.findByRole('img', { name: 'Archival regime momentum timeline' })).toBeInTheDocument()
  expect(screen.getByText(/Unknown original availability cannot become eligible knowledge/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'ML reliability' }))
  expect(await screen.findByRole('heading', { name: 'Model Reliability Matrix' })).toBeInTheDocument()
  expect(screen.getByText('NOT ELIGIBLE')).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Reliability horizon' })).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Reliability metric'), 'brier_score')
  expect(screen.getByRole('heading', { name: 'Development balanced-accuracy fold dispersion' })).toBeInTheDocument()
})

it('typed contracts reject a falsely authorized forecast and preserve null confidence', () => {
  expect(passportSchema.safeParse(passport.data).success).toBe(true)
  expect(regimeSchema.safeParse(regime.data).success).toBe(true)
  expect(reliabilitySchema.safeParse(reliability.data).success).toBe(true)
  expect(passportSchema.safeParse({ ...passport.data, evidence_confidence_percentage: 99 }).success).toBe(false)
  expect(regimeSchema.safeParse({ ...regime.data, current_forecast: 'AVAILABLE' }).success).toBe(false)
})
