import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { marketResearchSchema, universePageSchema } from '../../src/api/nse-market'

// Real compiled private research. Retain metadata only, never price-bearing DOM or traces.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })

test('compiled full NSE discovery and expanded Top 5/10/20 match saved backend evidence without provider acquisition', async ({ page }) => {
  const requests: { path: string; method: string }[] = []
  page.on('request', request => {
    const url = new URL(request.url())
    if (url.pathname.startsWith('/api/v1/')) requests.push({ path: url.pathname, method: request.method() })
  })
  const loaded = page.waitForResponse(response => response.url().includes('/api/v1/nse-market/research?'))
  await page.goto('/nse-market')
  const initial = await loaded
  expect(initial.status()).toBe(200)
  const initialData = marketResearchSchema.parse((await initial.json()).data)
  expect(initialData.counts.verified_eligible_common_equities).toBe(3198)
  expect(initialData.counts.discoverable_eq_series_identities).toBe(2706)
  expect(initialData.counts.validated_historical_stocks).toBeGreaterThanOrEqual(100)
  expect(initialData.unfiltered_total).toBeGreaterThan(31)
  expect(initialData.accepted_current_rankings).toBe(0)
  expect(initialData.automatic_acquisition_enabled).toBe(false)
  await expect(page.getByRole('heading', { name: 'AlphaLens Investment Opportunity Research', exact: true })).toBeVisible()
  await expect(page.getByText(/NO_DEMONSTRATED_EDGE/).first()).toBeVisible()

  for (const size of [5, 10, 20]) {
    const backend = await page.request.get('/api/v1/nse-market/research?page=1&page_size=' + size)
    expect(backend.status()).toBe(200)
    const data = marketResearchSchema.parse((await backend.json()).data)
    expect(data.candidates.map(row => row.key)).toEqual([...data.candidates].sort((a, b) => b.score - a.score || a.key.localeCompare(b.key)).map(row => row.key))
    await page.getByLabel('Expanded research list size').selectOption(String(size))
    const table = page.getByRole('table', { name: 'Expanded genuine model rankings', exact: true })
    await expect(table.locator('tbody tr')).toHaveCount(Math.min(size, data.total))
    for (const candidate of data.candidates) {
      const rendered = table.locator('tr[data-instrument-key="' + candidate.key + '"]')
      await expect(rendered.getByTestId('expanded-model-score')).toContainText(candidate.score.toFixed(6))
      await expect(rendered.getByRole('link', { name: candidate.symbol, exact: true })).toHaveAttribute('href', '/stocks/' + encodeURIComponent('upstox:' + candidate.key))
      await expect(rendered).toContainText(String(candidate.identity.name))
      expect(candidate.identity.provider_key).toBe(candidate.key)
      expect(candidate.identity.isin).toBe(candidate.key.split('|')[1])
      expect(candidate.features.length).toBe(candidate.feature_names.length)
    }
  }

  const matchedResponse = await page.request.get('/api/v1/nse-market/research?page=1&page_size=20&matches_only=true')
  expect(matchedResponse.status()).toBe(200)
  const matched = marketResearchSchema.parse((await matchedResponse.json()).data)
  await page.getByLabel('Only matches to supported preferences').check()
  await expect(page.getByTestId('expanded-model-score')).toHaveCount(Math.min(20, matched.total))
  expect(matched.candidates.every(row => row.preferences?.state === 'MATCHES_SUPPORTED_CONSTRAINTS')).toBe(true)

  const query = '3IINFOLTD'
  const source = await page.request.get('/api/v1/nse-market/universe?q=' + query)
  expect(source.status()).toBe(200)
  const universe = universePageSchema.parse((await source.json()).data)
  expect(universe.provider_requests).toBe(0)
  const identity = universe.rows.find(row => row.symbol === query)
  expect(identity).toBeTruthy()
  expect(identity?.instrument_type).toBe('BE')
  await page.getByLabel('Search current NSE common equities').fill(query)
  const identities = page.getByRole('table', { name: 'Verified current NSE universe', exact: true })
  await expect(identities.locator('tbody tr')).toHaveCount(universe.total)
  await expect(identities).toContainText(identity!.instrument_key)
  const privateSearch = await page.request.get('/api/v1/providers/upstox-private/instruments?q=' + query)
  expect(privateSearch.status()).toBe(200)
  const discovered = (await privateSearch.json()).data
  expect(discovered.candidate_count).toBe(3198)
  expect(discovered.market_prices_requested).toBe(false)
  expect(discovered.instruments.some((row: { provider_key: string }) => row.provider_key === identity!.instrument_key)).toBe(true)

  expect(requests.some(row => row.method !== 'GET')).toBe(false)
  expect(requests.some(row => /upstox-private\/(snapshot|watchlist|reference)/.test(row.path))).toBe(false)
  if (process.env.ALPHALENS_BROWSER_OUTPUT_DIR) writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR, 'full-nse-consolidation-metadata.json'), JSON.stringify({ current_common_equities: 3198, discoverable_eq_series: 2706, validated_historical_stocks: initialData.counts.validated_historical_stocks, actual_scored_stocks: initialData.unfiltered_total, top_5_10_20_backend_identity_score_match: true, matched_count: matched.total, non_eq_common_identity_search: true, provider_requests_from_page: 0, mutations: 0, accepted_rankings: 0, price_dom_retained: false }, null, 2))
})
