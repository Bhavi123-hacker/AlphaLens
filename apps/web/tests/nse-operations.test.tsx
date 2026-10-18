import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NseOperations } from '../src/components/NseOperations'

// TEST_ONLY presentation contracts; these counts are not real market evidence.
afterEach(() => vi.unstubAllGlobals())
it('shows the frozen cohort, zero matured outcomes and explicit unapproved limits', () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  render(<NseOperations operations={{ state: 'DRY_RUN', source_requests_last_run: 0, budget: {
    expected_securities: 500, max_stocks_per_run: 250, max_requests_per_run: 600,
    max_requests_per_day: 1800, cooldown_minutes: 60, cadence_ist: ['20:30', '21:30', '22:30'],
  } }} prospective={{ declarations: 1, unique_security_forecasts: 300, matured_security_outcomes: 0, complete_global_declarations: 0 }} />)
  expect(screen.getByText('Frozen expanded security forecasts').parentElement).toHaveTextContent('300')
  expect(screen.getByText('Genuinely matured expanded outcomes').parentElement).toHaveTextContent('0')
  expect(screen.getByText('Maximum provider GET attempts per run').parentElement).toHaveTextContent('600')
  expect(screen.getByText('Maximum provider GET attempts per IST day').parentElement).toHaveTextContent('1,800')
  expect(screen.getByText(/awaits explicit approval/)).toBeInTheDocument()
  expect(screen.getByTestId('nse-operational-state')).toHaveTextContent('Dry run')
  expect(fetch).not.toHaveBeenCalled()
})
it('keeps unknown request counts distinct from a zero-request replay', () => {
  render(<NseOperations operations={{ state: 'FAILED', source_requests_last_run: null, error_code: 'TEST_ONLY_CLOCK_UNAVAILABLE' }} />)
  expect(screen.getByText('Provider GETs in last saved run').parentElement).toHaveTextContent('Not observed')
  expect(screen.getByRole('status')).toHaveTextContent('Check readiness before retrying')
})
