import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { experimentalV2WorkspaceSchema } from '../../src/api/experimental-v2'

// Real compiled private workspace. Do not retain price-bearing DOM, traces or screenshots.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test('compiled V2 research matches genuine saved backend scores and preserves V1 isolation', async ({ page }) => {
  const paths: string[] = []
  page.on('request', request => { if (request.url().includes('/api/v1/')) paths.push(new URL(request.url()).pathname) })
  const pending = page.waitForResponse(response => response.url().includes('/api/v1/experimental-nse-v2/research'))
  await page.goto('/experimental-ai-v2')
  const response = await pending
  expect(response.status()).toBe(200)
  const data = experimentalV2WorkspaceSchema.parse((await response.json()).data)
  expect(data.available).toBe(true)
  expect(data.candidates.length).toBeGreaterThan(0)
  expect(data.accepted_current_rankings).toBe(0)
  await expect(page.getByRole('heading', { name: 'Experimental AI Stock Research V2', exact: true })).toBeVisible()
  await expect(page.getByText('EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED', { exact: true })).toBeVisible()
  for (const size of [5, 10, 20]) {
    await page.getByLabel('V2 research list size').selectOption(String(size))
    await expect(page.getByTestId('v2-model-score')).toHaveCount(Math.min(size, data.candidates.length))
  }
  for (const row of [...data.candidates].sort((a, b) => b.score - a.score || a.key.localeCompare(b.key)).slice(0, 20)) {
    const rendered = page.locator('tr[data-instrument-key="' + row.key + '"]')
    await expect(rendered.getByTestId('v2-model-score')).toHaveText(row.score.toFixed(6))
    await expect(rendered.getByRole('link', { name: row.symbol, exact: true })).toHaveAttribute('href', '/stocks/' + encodeURIComponent('upstox:' + row.key))
    expect(row.company_name).toBeTruthy()
    await expect(rendered.getByTestId('v2-company-name')).toHaveText(row.company_name!)
    expect(row.identity?.isin).toBe(row.key.split('|')[1])
    expect(row.technical_evidence?.length).toBeGreaterThan(0)
  }
  await expect(page.getByRole('heading', { name: 'Saved research operations', exact: true })).toBeVisible()
  if (data.prospective.outcomes === 0) await expect(page.getByText(/No matured V2 prospective outcomes exist yet/)).toBeVisible()
  const outstanding = Array.isArray(data.prospective.pending_forecasts) ? data.prospective.pending_forecasts : []
  if (outstanding.length) await expect(page.getByRole('table', { name: 'Outstanding genuine prospective evidence' }).locator('tbody tr')).toHaveCount(Math.min(outstanding.length, 100))
  await page.getByLabel('Only V2 matches to supported preferences').check()
  const matched = data.candidates.filter(row => row.preferences?.state === 'MATCHES_SUPPORTED_CONSTRAINTS')
  await expect(page.getByTestId('v2-model-score')).toHaveCount(Math.min(20, matched.length))
  expect(paths.some(path => path.includes('upstox-private/snapshot') || path.includes('upstox-private/watchlist'))).toBe(false)
  await expect(page.getByRole('link', { name: /V1 preserved experiment/ })).toHaveAttribute('href', '/experimental-ai')
  if (process.env.ALPHALENS_BROWSER_OUTPUT_DIR) writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR, 'experimental-v2-metadata.json'), JSON.stringify({ family: data.family, model_id: data.model?.id, dataset_id: data.dataset?.id, scored: data.candidates.length, displayed_top20: Math.min(20, data.candidates.length), preference_matches: matched.length, outcomes: data.prospective.outcomes, accepted_rankings: 0, score_identity_alignment: true, provider_market_requests_from_page: 0, market_values_retained: false }, null, 2))
})
