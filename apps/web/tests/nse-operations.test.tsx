import { afterEach, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NseOperations } from '../src/components/NseOperations'

// TEST_ONLY presentation contracts; these counts are not real market evidence.
afterEach(() => vi.unstubAllGlobals())
it('separates a pending collection target from older qualified history and labels CPU fallback', () => {
  const fetch=vi.fn();vi.stubGlobal('fetch',fetch)
  render(<NseOperations operations={{
    session_status:{session:'2026-10-19',updated_or_already_verified:499,pending_securities:1,failed_securities:0},
    target_session_status:{session:'2026-10-21',configured_securities:500,updated_or_already_verified:0,pending_securities:500},
    processing:{state:'SAVED_BENCHMARK_NOT_PRODUCTION_EXECUTION',completed_at:'2026-10-21T15:05:00Z',
      capability:{torch_version:'TEST_ONLY_CPU',cuda_available:false,xpu_available:false},gpu_speedup:null,
      measurements:[{method:'AUTO_BATCHED',completed_device:'cpu',sequences:1000,median_seconds:.02,sequences_per_second:50000,repeated_input_stress_test:true,fallback_reason:'REQUESTED_ACCELERATOR_UNAVAILABLE'}]},
  }}/>)
  expect(screen.getByTestId('collection-coverage-summary')).toHaveTextContent('499 verified, 1 pending')
  expect(screen.getByTestId('target-session-status')).toHaveTextContent('0 / 500 qualified; 500 pending')
  expect(screen.getByText(/GPU speedup unavailable/)).toBeInTheDocument()
  expect(screen.getByRole('table',{name:'Saved inference throughput',hidden:true})).toHaveTextContent('Repeated saved inputs; not unique securities')
  expect(fetch).not.toHaveBeenCalled()
})
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
  expect(screen.getByText('GET attempts in last terminal run').parentElement).toHaveTextContent('Not observed')
  expect(screen.getByRole('status')).toHaveTextContent('Check readiness before retrying')
})

it('uses full cohort coverage and separates actual requests, reservations and terminal receipts', () => {
  const fetch=vi.fn();vi.stubGlobal('fetch',fetch)
  const completed='2026-10-19T17:00:08.045134+00:00'
  render(<NseOperations coverage={{end:'2026-10-16',per_security:[{last:'2026-10-16'}],latest_session_coverage:{session:'2026-10-16',verified_securities:499,configured_securities:500,pending_securities:1,basis:'FULL_CONFIGURED_COHORT_BEFORE_PAGINATION'}}} operations={{state:'FAILED',source_requests_last_run:999,
    last_completed:{state:'FAILED',source_requests_last_run:0,completed_at:completed},
    reservations:{quota_day:'2026-10-19',reserved_get_attempts:600},
    shared_provider_usage:{state:'AVAILABLE',recorded_get_attempts:1,completed_get_attempts:1,unresolved_attempts:0,as_of:'2026-10-19T17:03:00+00:00'},
    unfinished_attempts_total:1,unfinished_attempts:[{run_id:'TEST_ONLY',started_at:'2026-10-19T16:00:26+00:00',state:'INCOMPLETE_NO_TERMINAL_RECEIPT',reserved_get_attempts:600}]
  }}/>)
  expect(screen.getByText('Stocks with latest retained session').parentElement).toHaveTextContent('499 / 500')
  expect(screen.getByText('Shared provider GET attempts today').parentElement).toHaveTextContent('1')
  expect(screen.getByText('Reserved GET attempts today').parentElement).toHaveTextContent('600')
  expect(screen.getByText('GET attempts in last terminal run').parentElement).toHaveTextContent('0')
  expect(screen.getAllByText(/2026-10-19T17:00:08.045134/).length).toBeGreaterThan(0)
  expect(screen.getByText('Collection failed')).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})
