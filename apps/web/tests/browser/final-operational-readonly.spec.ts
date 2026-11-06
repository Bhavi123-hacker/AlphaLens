import { test, expect } from '@playwright/test'
import { currency } from '../../src/lib/format'

// Real existing isolated operator records; these manual test lots are not market executions.
test.use({ trace: 'off', screenshot: 'off', video: 'off' })
test('saved portfolio FIFO, preferences and research routes remain operational without provider refresh or mutations', async ({ page }) => {
  const requests: { path: string; method: string }[] = []
  page.on('request', request => { if (request.url().includes('/api/v1/')) requests.push({ path: new URL(request.url()).pathname + new URL(request.url()).search, method: request.method() }) })
  const workspace = await page.request.get('/api/v1/personal/workspace')
  expect(workspace.status()).toBe(200)
  const saved = (await workspace.json()).data
  const portfolio = saved.portfolios.find((row: { name: string; event_count: number }) => row.name.startsWith('TEST_ONLY P33 funded') && row.event_count === 4)
  expect(portfolio).toBeTruthy()
  const review = await page.request.get('/api/v1/personal/portfolios/' + portfolio.id)
  expect(review.status()).toBe(200)
  const data = (await review.json()).data
  expect(data.realized_pnl_exact).toBe('1585')
  expect(data.holdings[0].cost_basis_exact).toBe('600')
  expect(data.cash_balance).toBeNull()
  expect(data.portfolio_value).toBeNull()
  await page.goto('/my-portfolio')
  await page.getByLabel('My portfolio', { exact: true }).selectOption(portfolio.id)
  await expect(page.getByText('Recorded realized P&L', { exact: true }).locator('..').locator('strong')).toHaveText('₹' + currency(data.realized_pnl))
  await expect(page.getByText('Remaining FIFO cost basis', { exact: true }).locator('..').locator('strong')).toHaveText('₹' + currency(data.remaining_cost_basis))
  for (const [path, heading] of [['/preferences', 'My Research Preferences'], ['/decision-desk', 'Research Decision Desk'], ['/journal', 'Portfolio Research Journal']]) {
    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  }
  expect(requests.some(row => row.method !== 'GET')).toBe(false)
  expect(requests.some(row => row.path.includes('refresh=true') || row.path.includes('upstox-private/snapshot') || row.path.includes('upstox-private/watchlist'))).toBe(false)
})

test('retained genuine EOD supports an indicative exit without changing the recorded FIFO ledger', async ({ page }) => {
  const saved = (await (await page.request.get('/api/v1/personal/workspace')).json()).data
  const portfolio = saved.portfolios.find((row: { name: string; event_count: number }) => row.name.startsWith('TEST_ONLY P33 funded') && row.event_count === 4)
  expect(portfolio).toBeTruthy()
  await page.goto('/my-portfolio')
  await page.getByLabel('My portfolio', { exact: true }).selectOption(portfolio.id)
  const reviewed = (await (await page.request.get('/api/v1/personal/portfolios/' + portfolio.id)).json()).data
  expect(reviewed.valuation_status).toBe('INDICATIVE_UNRECONCILED_ACTIONS_NOT_P15_ACCEPTED_VALUATION')
  expect(reviewed.holdings[0].mark.basis).toBe('RETAINED_ADJUSTED_EOD_INDICATIVE_UNRECONCILED_ACTIONS')
  expect(reviewed.holdings[0].mark.source).toBe('UPSTOX_PRIVATE_RETAINED_DAILY_CANDLE')
  expect(reviewed.holdings[0].mark.financial_accepted_valuation).toBe(false)
  expect(reviewed.portfolio_value).toBeNull()
  await page.getByLabel('Scenario stock', { exact: true }).selectOption(reviewed.holdings[0].instrument_key)
  await page.getByLabel('Hypothetical share change', { exact: true }).fill('-1')
  await page.getByLabel('Hypothetical transaction costs (INR)', { exact: true }).fill('5')
  const response = page.waitForResponse(reply => reply.url().endsWith('/scenario'))
  await page.getByRole('button', { name: 'Calculate scenario', exact: true }).click()
  const scenario = (await (await response).json()).data
  expect(scenario.exit_impact.state).toBe('HYPOTHETICAL_P15_FIFO_NOT_REALIZED_ACTIVITY')
  expect(scenario.exit_impact.remaining_quantity).toBe('2')
  expect(scenario.exit_impact.remaining_basis_exact).toBe('400')
  expect(scenario.writes_performed).toBe(false)
  const after = (await (await page.request.get('/api/v1/personal/portfolios/' + portfolio.id)).json()).data
  expect(after.ledger_state_id).toBe(reviewed.ledger_state_id)
  expect(after.realized_pnl_exact).toBe('1585')
})
