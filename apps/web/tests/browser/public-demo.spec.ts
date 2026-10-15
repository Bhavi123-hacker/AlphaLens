import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('static demo charts, filters and passport work without a private API', async ({ page }) => {
  const requested: string[] = []
  page.on('request', r => requested.push(r.url()))
  await page.goto('./')
  await expect(page.getByText(/SYNTHETIC DEMONSTRATION/)).toBeVisible()
  await expect(page.getByRole('img', { name: 'Synthetic example candlestick and SMA20 chart' })).toBeVisible()
  await page.getByRole('button', { name: '30 slots', exact: true }).click()
  await expect(page.getByRole('button', { name: '30 slots', exact: true })).toHaveAttribute('aria-pressed','true')
  await page.getByRole('button', { name: 'Market map', exact: true }).click()
  await expect(page.getByRole('img', { name: 'Synthetic market heatmap' })).toBeVisible()
  await page.getByLabel('Search synthetic instruments', { exact: true }).fill('DEMO001')
  await expect(page.getByText('1 of128 generated examples · not an NSE universe')).toBeVisible()
  await page.getByRole('button', { name: 'Evidence passport', exact: true }).click()
  await expect(page.getByText('Why this example is not recommended')).toBeVisible()
  await expect(page.getByRole('img', { name: 'Synthetic example feature completeness' })).toBeVisible()
  expect(requested.some(url => url.includes('/api/'))).toBe(false)
  expect(requested.every(url => new URL(url).origin === new URL(process.env.ALPHALENS_DEMO_BASE_URL ?? 'http://127.0.0.1:8031').origin)).toBe(true)
})

test('public demonstration is keyboard accessible and responsive', async ({ page }) => {
  await page.goto('./')
  await page.getByRole('button', { name: 'Research methodology', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Research intelligence, not a trading promise.' })).toBeVisible()
  const result = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa']).analyze()
  expect(result.violations).toEqual([])
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('static package CSP rejects private API connections and contains no real instruments', async ({ page }) => {
  await page.goto('./')
  expect(await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content')).toContain("connect-src 'none'")
  await expect(page.getByText('No private research, account, credential or financial record is bundled')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'RELIANCE', exact: true })).toHaveCount(0)
})

test('synthetic preferences, FIFO stages, review desk and journal are interactive and isolated', async ({page})=>{
  const requests:string[]=[];page.on('request',r=>requests.push(r.url()));await page.goto('./')
  await page.getByRole('button',{name:'Preferences & Portfolio',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Preferences & Portfolio',exact:true})).toBeVisible()
  await page.getByLabel('Constructed ledger stage',{exact:true}).selectOption('2')
  await expect(page.getByText(/constructed realized FIFO gain: 1585.00/)).toBeVisible()
  await page.getByLabel('Sample maximum stock allocation (%)',{exact:true}).fill('40')
  await expect(page.getByText(/CONCENTRATION REVIEW/)).toBeVisible()
  await page.getByLabel('Sample research hypothesis',{exact:true}).fill('TEST_ONLY synthetic research note')
  await expect(page.getByText('Preview: TEST_ONLY synthetic research note',{exact:true})).toBeVisible()
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze();expect(axe.violations).toEqual([])
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  expect(requests.some(r=>r.includes('/api/'))).toBe(false)
})
