import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Authenticated isolated compiled server, real saved evidence, acquisition blocked server-side.
test.use({trace:'off',screenshot:'off',video:'off'})
test('saved processing and target-session monitoring match the backend without acquisition', async ({page})=>{
  const paths:string[]=[]
  page.on('request',r=>paths.push(new URL(r.url()).pathname))
  const loaded=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/nse-market/research')
  await page.goto('/nse-market')
  const response=await loaded
  expect(response.status()).toBe(200)
  const data=(await response.json()).data
  const operations=data.operations
  const coverage=operations.session_status
  await expect(page.getByTestId('collection-coverage-summary')).toContainText(`${coverage.updated_or_already_verified} verified, ${coverage.pending_securities} pending`)
  if(operations.target_session_status){
    const target=operations.target_session_status
    await expect(page.getByTestId('target-session-status')).toContainText(`${target.updated_or_already_verified} / ${target.configured_securities} qualified; ${target.pending_securities} pending`)
  }
  await page.getByText('Processing mode and measured inference throughput',{exact:true}).click()
  expect(operations.processing.state).toBe('SAVED_BENCHMARK_NOT_PRODUCTION_EXECUTION')
  await expect(page.getByRole('table',{name:'Saved inference throughput'})).toContainText('Repeated saved inputs; not unique securities')
  await expect(page.getByText(/Production execution: unchanged CPU predictor/)).toBeVisible()
  if(operations.processing.gpu_speedup===null) await expect(page.getByText(/GPU speedup unavailable/)).toBeVisible()
  const evaluated=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/nse-market/prospective-evaluation')
  await page.getByText('Inspect point-in-time prospective evidence').click()
  const actual=(await (await evaluated).json()).data
  expect(actual.raw_forecast_records).toBeGreaterThanOrEqual(633)
  expect(actual.provider_requests).toBe(0)
  if(actual.matured_outcomes===0) expect(actual.metrics.score.accuracy).toBeNull()
  expect(paths.some(path=>/upstox-private\/(snapshot|watchlist|reference)/.test(path))).toBe(false)
  const axe=await new AxeBuilder({page}).include('#daily-research').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
  expect(axe.violations).toEqual([])
})
