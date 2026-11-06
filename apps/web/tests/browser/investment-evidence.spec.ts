import { test, expect } from '@playwright/test'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { marketResearchSchema } from '../../src/api/nse-market'

// Real saved provider-backed evidence, isolated operator; no interception or data fixtures.
test.use({trace:'off',screenshot:'off',video:'off'})
test('saved research constraints round trip through the compiled editor and restore the isolated profile',async({page})=>{
  const originalResponse=await page.request.get('/api/v1/personal/workspace')
  expect(originalResponse.status()).toBe(200)
  const original=(await originalResponse.json()).data.profile.value
  await page.goto('/nse-market')
  await page.getByText('Review or update my research constraints',{exact:true}).click()
  const budget=page.getByLabel('Research budget INR',{exact:true})
  await expect(budget).toBeVisible()
  try {
    await budget.fill('10000')
    const saved=page.waitForResponse(r=>r.url().endsWith('/personal/profile')&&r.request().method()==='POST')
    const refreshed=page.waitForResponse(r=>r.url().endsWith('/personal/workspace'))
    await page.getByRole('button',{name:'Save research constraints',exact:true}).click()
    expect((await saved).status()).toBe(200)
    await refreshed
    await expect(page.getByText(/Preferences saved; research matches refreshed/)).toBeVisible()
    const check=await page.request.get('/api/v1/personal/workspace')
    expect((await check.json()).data.profile.value.budget_inr).toBe('10000')
  } finally {
    await budget.fill(original.budget_inr??'')
    const restored=page.waitForResponse(r=>r.url().endsWith('/personal/profile')&&r.request().method()==='POST')
    await page.getByRole('button',{name:'Save research constraints',exact:true}).click()
    expect((await restored).status()).toBe(200)
    const checked=await page.request.get('/api/v1/personal/workspace')
    expect((await checked.json()).data.profile.value).toEqual(original)
  }
})
test('compiled horizon views, economic evidence and adverse scenarios match backend', async ({page})=>{
  const requests:string[]=[]
  page.on('request',request=>{const path=new URL(request.url()).pathname;if(path.startsWith('/api/v1/'))requests.push(path)})
  await page.goto('/nse-market')
  await expect(page.getByRole('heading',{name:'AlphaLens Investment Opportunity Research',exact:true})).toBeVisible()
  const table=page.getByRole('table',{name:'Expanded genuine model rankings',exact:true})
  for(const horizon of [5,10,20]) {
    const response=await page.request.get(`/api/v1/nse-market/research?page_size=5&horizon=${horizon}`)
    expect(response.status()).toBe(200)
    const data=marketResearchSchema.parse((await response.json()).data)
    expect(data.research_horizon_sessions).toBe(horizon)
    expect(data.ml_horizon_supported).toBe(horizon===5)
    expect(data.provider_requests).toBe(0)
    await page.getByLabel('Research horizon',{exact:true}).selectOption(String(horizon))
    await expect(table.locator('tbody tr')).toHaveCount(data.candidates.length)
    for(let i=0;i<data.candidates.length;i++) {
      const row=data.candidates[i]
      await expect(table.locator('tbody tr').nth(i)).toHaveAttribute('data-instrument-key',row.key)
      await expect(table.locator('tbody tr').nth(i).getByTestId('expanded-model-score')).toContainText(row.score.toFixed(6))
    }
    if(horizon!==5) await expect(page.getByTestId('research-horizon-basis')).toContainText('No trained forecast')
  }
  const economics=await page.request.get('/api/v1/nse-market/economic-research')
  expect(economics.status()).toBe(200)
  const report=(await economics.json()).data
  expect(report.policy_count).toBe(4)
  expect(report.provider_requests).toBe(0)
  expect(report.policies.every((p:{scenarios:{net_compounded_reference_return:number}[]})=>p.scenarios[1].net_compounded_reference_return<0)).toBe(true)
  await page.getByText('Inspect economic attribution and the bounded lower-frequency experiment',{exact:true}).click()
  await expect(page.getByRole('table',{name:'Registered sparse entry policies'}).locator('tbody tr')).toHaveCount(4)
  await table.getByText('Why this security qualifies, risks and scenarios',{exact:true}).first().click()
  await expect(table.getByText('No demonstrated predictive or net economic edge',{exact:true})).toBeVisible()
  const sizing=table.getByText('Hypothetical allocation under your explicit risk-budget assumptions',{exact:true}).first()
  await sizing.click()
  await table.getByLabel('Research capital').fill('100000')
  await table.getByLabel('Assumed loss budget').fill('10000')
  await table.getByLabel('Assumed stop distance %').fill('5')
  await table.getByLabel('Assumed round-trip costs bps').fill('50')
  const scenario=page.waitForResponse(response=>response.url().includes('/nse-market/position-scenario?'))
  await table.getByRole('button',{name:'Calculate hypothetical units'}).click()
  const calculated=(await(await scenario).json()).data
  expect(calculated.writes_performed).toBe(false)
  expect(calculated.model_score_used_for_sizing).toBe(false)
  const losses=table.getByRole('table',{name:'Hypothetical adverse price moves'})
  await expect(losses.locator('tbody tr')).toHaveCount(3)
  for(const row of calculated.adverse_scenarios) await expect(losses).toContainText(row.loss_including_cost)
  expect(requests.some(path=>/upstox-private\/(snapshot|watchlist|reference)/.test(path))).toBe(false)
  if(process.env.ALPHALENS_BROWSER_OUTPUT_DIR)writeFileSync(join(process.env.ALPHALENS_BROWSER_OUTPUT_DIR,'investment-evidence-metadata.json'),JSON.stringify({horizons:[5,10,20],five_session_scores_not_relabelled:true,backend_order_match:true,registered_policy_count:4,positive_central_policy_count:0,adverse_scenarios:3,provider_requests:0,portfolio_writes:0,private_values_retained:false},null,2))
})
