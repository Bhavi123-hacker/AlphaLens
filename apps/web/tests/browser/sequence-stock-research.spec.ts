import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'

// Genuine saved observations and model outputs. No price bodies, screenshots or traces retained.
process.env.PLAYWRIGHT_NO_COPY_PROMPT = '1'
test.use({ trace: 'off', screenshot: 'off', video: 'off' })

test('stock-specific LSTM evidence and explicit research sizing match genuine saved backend inputs', async ({ page }) => {
  test.setTimeout(120_000)
  const source = await page.request.get('/api/v1/nse-market/sequence')
  expect(source.status()).toBe(200)
  const sequence = (await source.json()).data
  expect(sequence.state).toBe('EXPERIMENTAL_UNVALIDATED')
  expect(sequence.current_scored_count).toBeGreaterThan(0)
  expect(sequence.accepted_rankings).toBe(0)
  expect(sequence.prospective_forecasts).toBe(0)
  const scored = sequence.current_scores[0] as { key: string; score: number; model_sha256: string }
  const paths: string[] = []
  page.on('request', request => { if (request.url().includes('/api/v1/')) paths.push(new URL(request.url()).pathname) })
  await page.goto('/stocks/' + encodeURIComponent('upstox:' + scored.key))
  const received = page.waitForResponse(response => response.url().includes('/nse-market/stock-research?'))
  await page.getByText('Inspect experimental predictions, baselines and observed historical outcomes', { exact: true }).click()
  const response = await received
  expect(response.status()).toBe(200)
  const data = (await response.json()).data
  expect(data.key).toBe(scored.key)
  expect(data.lstm.key).toBe(scored.key)
  expect(data.lstm.score).toBe(scored.score)
  expect(data.lstm.model_sha256).toBe(scored.model_sha256)
  expect(data.lstm.forecast_created).toBe(false)
  expect(Date.parse(data.lstm.source_observed_at) <= Date.parse(data.lstm.inference_at)).toBe(true)
  expect(Date.parse(data.lstm.inference_at) <= Date.now()).toBe(true)
  expect(data.accepted_rankings).toBe(0)
  expect(data.prospective_outcomes).toBe(0)
  await expect(page.getByText('Sequence LSTM score', { exact: true }).locator('..').locator('strong')).toHaveText(scored.score.toFixed(6))
  if (data.historical_comparisons.length) await expect(page.getByRole('img', { name: 'Known-period model versus observed outcomes; no prospective performance', exact: true })).toBeVisible()
  expect(data.historical_comparisons.every((row: { decision_session: string; target_session: string }) => row.decision_session < row.target_session && Date.parse(row.target_session) <= Date.now())).toBe(true)
  await page.getByText('Hypothetical allocation under your explicit risk-budget assumptions', { exact: true }).click()
  await page.getByLabel(/^Research capital/).fill('100000')
  await page.getByLabel(/^Assumed loss budget/).fill('1000')
  await page.getByLabel('Assumed stop distance %', { exact: true }).fill('5')
  await page.getByLabel('Assumed round-trip costs bps', { exact: true }).fill('25')
  const calculated = page.waitForResponse(reply => reply.url().includes('/nse-market/position-scenario?'))
  await page.getByRole('button', { name: 'Calculate hypothetical units', exact: true }).click()
  const sizingResponse = await calculated
  expect(sizingResponse.status()).toBe(200)
  const sizing = (await sizingResponse.json()).data
  expect(sizing.key).toBe(scored.key)
  expect(sizing.writes_performed).toBe(false)
  expect(sizing.stop_is_guaranteed).toBe(false)
  expect(sizing.verified_cash_balance).toBeNull()
  expect(sizing.model_score_used_for_sizing).toBe(false)
  expect(Number.isInteger(sizing.quantity_whole_units)).toBe(true)
  await expect(page.getByText(new RegExp('^' + sizing.quantity_whole_units + ' whole illustrative units\\.'))).toBeVisible()
  expect(paths.some(path => /upstox-private\/(snapshot|watchlist|reference)/.test(path))).toBe(false)
  if (process.env.ALPHALENS_BROWSER_OUTPUT_DIR) writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR, 'sequence-stock-research-metadata.json'), JSON.stringify({ actual_model_sha256: scored.model_sha256, exact_saved_score_identity_match: true, current_scored_count: sequence.current_scored_count, historical_comparison_count: data.historical_comparisons.length, historical_classification: data.historical_classification, sizing_uses_explicit_assumptions: true, sizing_writes: false, source_acquisition_requests: 0, matured_prospective_outcomes: 0, accepted_rankings: 0, price_values_retained: false }, null, 2))
})
