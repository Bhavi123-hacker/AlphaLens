import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

// Only the published synthetic site is captured; no private session or provider data.
const destination = resolve('../../docs/screenshots')
await mkdir(destination, { recursive: true })
const browser = await chromium.launch({ channel: 'chromium' })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } })
  await page.goto('https://bhavi123-hacker.github.io/AlphaLens/')
  await page.getByText(/SYNTHETIC DEMONSTRATION/).waitFor()
  await page.getByRole('img', { name: 'Synthetic example candlestick and SMA20 chart' }).waitFor()
  await page.screenshot({ path: resolve(destination, 'p30-synthetic-desktop.png') })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: resolve(destination, 'p30-synthetic-mobile.png') })
  process.stdout.write('PUBLIC_SYNTHETIC_SCREENSHOTS_CAPTURED\n')
} finally {
  await browser.close()
}
