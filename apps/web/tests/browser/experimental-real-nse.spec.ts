import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { signIn } from './auth-setup'
import { experimentalWorkspaceSchema } from '../../src/api/experimental'

// Genuine protected local evidence. No interceptions, fixture scores or price-bearing artifacts.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test('compiled experimental workspace displays the saved model scores and exact instrument identities', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/login')
  await signIn(page)
  const requested: string[] = []
  page.on('request', request => {
    if (request.url().includes('/api/v1/')) requested.push(new URL(request.url()).pathname)
  })
  const evidence = page.waitForResponse(response => response.url().includes('/api/v1/experimental-nse/research'))
  await page.goto('/experimental-ai')
  const response = await evidence
  expect(response.status()).toBe(200)
  const body = await response.json()
  const data = experimentalWorkspaceSchema.parse(body.data)
  expect(data.available).toBe(true)
  expect(data.candidates.length).toBeGreaterThan(0)
  expect(data.accepted_current_rankings).toBe(0)
  await expect(page.getByRole('heading', { name: 'Experimental AI Stock Research', exact: true })).toBeVisible()
  await expect(page.getByText('EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED', { exact: true })).toBeVisible()
  for (const size of [5, 10, 20]) {
    await page.getByLabel('Experimental research list size').selectOption(String(size))
    await expect(page.getByTestId('experimental-score')).toHaveCount(Math.min(size, data.candidates.length))
  }
  const rows = [...data.candidates].sort((a, b) => b.score - a.score || a.key.localeCompare(b.key)).slice(0, 20)
  await expect(page.getByTestId('experimental-score')).toHaveCount(rows.length)
  for (const row of rows) {
    const rendered = page.locator('tr[data-instrument-key="' + row.key + '"]')
    await expect(rendered.getByTestId('experimental-score')).toContainText(row.score.toFixed(6))
    await expect(rendered.getByRole('link', { name: row.symbol, exact: true })).toHaveAttribute('href', '/stocks/' + encodeURIComponent('upstox:' + row.key))
  }
  await page.getByLabel('Only matches to supported preferences').check()
  const matching = data.candidates.filter(row => row.preferences?.state === 'MATCHES_SUPPORTED_CONSTRAINTS').slice(0, 20)
  await expect(page.getByTestId('experimental-score')).toHaveCount(matching.length)
  expect(requested.some(path => path.includes('upstox-private/snapshot') || path.includes('upstox-private/watchlist'))).toBe(false)
  expect(data.prospective.outcomes).toBe(0)
  if (process.env.ALPHALENS_BROWSER_OUTPUT_DIR) writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR, 'experimental-real-nse-metadata.json'), JSON.stringify({ family: data.family, model_id: data.model?.id, dataset_id: data.dataset?.id, scored_securities: data.candidates.length, displayed_top20: rows.length, value_identity_alignment: true, preference_matches: matching.length, prospective_outcomes: data.prospective.outcomes, accepted_rankings: 0, provider_market_requests_from_page: 0, prices_and_scores_retained: false }, null, 2))
})
