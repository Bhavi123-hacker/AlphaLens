import { expect, test } from '@playwright/test'

// TEST_ONLY browser contracts over the compiled private app. Every API response
// below is constructed; no provider, authentication store or saved data is used.
function evidence(data: unknown) {
  return { data, source: 'TEST_ONLY', version: 'TEST_ONLY', as_of_session: null,
    artifact_id: null, provenance: {}, evidence_status: 'AVAILABLE', quality_status: 'TEST_ONLY',
    missing_data_reasons: [], page: null, classification: { data_reality: 'TEST_ONLY',
      usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null,
      p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' } }
}
test('TEST_ONLY empty acquisition, unavailable outcomes and budget evidence remain distinct in a compiled browser', async ({ page, baseURL }) => {
  const requests: string[] = []
  const forbidden: string[] = []
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url())
    if (url.origin !== new URL(baseURL!).origin) { forbidden.push(url.origin); return route.abort() }
    if (!url.pathname.startsWith('/api/')) return route.continue()
    requests.push(url.pathname + url.search)
    if (request.method() !== 'GET' || url.searchParams.get('refresh') === 'true'
      || /upstox-private/.test(url.pathname)) { forbidden.push(url.pathname); return route.abort() }
    let data: unknown = {}
    if (url.pathname.endsWith('/auth/session')) return route.fulfill({ json: {
      account_id: 'TEST_ONLY', username: 'TEST_ONLY', role: 'ADMIN', session_id: 'TEST_ONLY',
      csrf_token: 'TEST_ONLY', absolute_expires: Math.floor(Date.now() / 1000) + 3600, idle_seconds: 1800,
    } })
    if (url.pathname.endsWith('/nse-market/universe')) data = { snapshot_id: 'TEST_ONLY', observed_at: '2026-10-21T15:00:00Z',
      total: 0, page: 1, page_size: 25, provider_requests: 0, summary: {}, rows: [] }
    else if (url.pathname.endsWith('/nse-market/research')) data = { state: 'AVAILABLE', counts: {
      verified_eligible_common_equities: 500, validated_historical_stocks: 499,
      experimental_ml_eligible_stocks: 0, independently_accepted_ml_stocks: 0,
    }, coverage: { start: '2026-10-19', end: '2026-10-19' }, scores: null, candidates: [],
      total: 0, unfiltered_total: 0, page: 1, page_size: 5, provider_requests: 0,
      accepted_current_rankings: 0, automatic_acquisition_enabled: false,
      operations: { state: 'PARTIAL_OR_PUBLICATION_PENDING',
        windows_task: { state: 'Ready', observed_at: new Date().toISOString() },
        budget: { expected_securities: 500, max_stocks_per_run: 250,
          max_requests_per_run: 600, max_requests_per_day: 1800, cooldown_minutes: 60 },
        session_status: { session: '2026-10-19', updated_or_already_verified: 499, pending_securities: 1, failed_securities: 0 },
        target_session_status: { session: '2026-10-21', configured_securities: 500, updated_or_already_verified: 0, pending_securities: 500 },
        shared_provider_usage: { recorded_get_attempts: 251, completed_get_attempts: 251, unresolved_attempts: 0, ist_day: '2026-10-21' },
        reservations: { reserved_get_attempts: 600, quota_day: '2026-10-21' },
      }, prospective_cohort: { matured_security_outcomes: 0 } }
    else if (url.pathname.endsWith('/nse-market/prospective-evaluation')) data = {
      as_of: '2026-10-21T16:00:00Z', raw_forecast_records: 0, unique_decisions: 0, matured_outcomes: 0,
      not_evaluated_decisions: 0, provider_requests: 0,
      metrics: { score: { samples: 0, accuracy: null, balanced_accuracy: null, brier_score: null } },
    }
    else if (url.pathname.endsWith('/alerts/unread-count')) data = { unread_count: 0 }
    else if (url.pathname.endsWith('/status/freshness')) data = { last_evidenced_market_session: '2026-10-19' }
    return route.fulfill({ json: evidence(data) })
  })
  await page.goto('/nse-market')
  await expect(page.getByText('TEST_ONLY DEMONSTRATION - Synthetic evidence. No real prices, forecasts or market performance.')).toBeVisible()
  await expect(page.getByTestId('collection-coverage-summary')).toContainText('499 verified, 1 pending')
  await expect(page.getByTestId('target-session-status')).toContainText('0 / 500 qualified; 500 pending')
  await expect(page.getByText('Reserved GET attempts today').locator('..')).toContainText('600')
  await expect(page.getByText('Shared provider GET attempts today').locator('..')).toContainText('251')
  await page.getByText('Inspect point-in-time prospective evidence').click()
  const table = page.getByRole('table', { name: 'Prospective model and baseline evaluation' })
  await expect(table).toContainText('Unavailable')
  await expect(table).not.toContainText('0.00%')
  await expect(page.getByText('PROSPECTIVE_EVALUATION_PENDING', { exact: true })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  const open = page.getByRole('button', { name: 'Open navigation', exact: true })
  await open.click()
  await expect(page.getByRole('dialog', { name: 'Primary navigation' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(open).toBeFocused()
  expect(forbidden).toEqual([])
  expect(requests.some(path => path.includes('/prospective-evaluation'))).toBe(true)
})

test('TEST_ONLY missing backend remains a sign-in failure instead of displaying invented observations', async ({ page, baseURL }) => {
  await page.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (url.origin !== new URL(baseURL!).origin) return route.abort()
    if (url.pathname.startsWith('/api/')) return route.fulfill({ status: 503, json: { code: 'TEST_ONLY_DATABASE_UNAVAILABLE' } })
    return route.continue()
  })
  await page.goto('/nse-market')
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('local security request was rejected')
  await expect(page.getByTestId('expanded-model-score')).toHaveCount(0)
})
