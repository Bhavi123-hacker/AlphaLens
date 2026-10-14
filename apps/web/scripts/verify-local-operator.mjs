// Credential input arrives through stdin only. No screenshots/traces/password files.
import { chromium } from '@playwright/test'
let input = ''
for await (const part of process.stdin) input += part
let browser
try {
  const value = JSON.parse(input); input = ''
  browser = await chromium.launch({ channel: 'chromium', executablePath: 'D:/al-research/p18-runtime/browsers/chromium-1248/chrome-win64/chrome.exe' })
  const page = await browser.newPage()
  await page.goto('http://127.0.0.1:8017/login')
  await page.getByLabel('Username', { exact: true }).fill(value.username)
  await page.getByLabel('Password', { exact: true }).fill(value.password)
  value.password = ''; value.username = ''
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL(url => !url.pathname.endsWith('/login'), { timeout: 30000 })
  const response = await page.request.get('http://127.0.0.1:8017/api/v1/providers/upstox-validation')
  if (response.status() !== 200) throw new Error('Protected read failed')
  await page.goto('http://127.0.0.1:8017/settings')
  await page.getByRole('button', { name: 'Log out', exact: true }).click()
  await page.getByRole('heading', { name: 'Sign in', exact: true }).waitFor()
  if ((await page.request.get('http://127.0.0.1:8017/api/v1/providers/upstox-validation')).status() !== 401) throw new Error('Logout failed')
} catch {
  process.exitCode = 1
} finally { if (browser) await browser.close() }
