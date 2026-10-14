// Real compiled app, isolated test operator; only geometry/state output, no prices.
import { chromium } from '@playwright/test'
import { readFileSync } from 'node:fs'
const input = JSON.parse(readFileSync('../../.local-data/p31-browser-runtime/credentials.json', 'utf8'))
const browser = await chromium.launch({ executablePath: 'D:/al-research/p18-runtime/browsers/chromium-1248/chrome-win64/chrome.exe' })
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await page.goto('http://127.0.0.1:8029/login')
  await page.getByLabel('Username', { exact: true }).fill(input.username)
  await page.getByLabel('Password', { exact: true }).fill(input.password)
  input.password = ''; input.username = ''
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('heading', { name: 'Sign in', exact: true }).waitFor({ state: 'hidden' })
  await page.goto('http://127.0.0.1:8029/research')
  await page.getByRole('cell', { name: 'Hist gradient boosting', exact: true }).first().waitFor()
  const result = await page.evaluate(() => ({ viewport: globalThis.innerWidth, document: globalThis.document.documentElement.scrollWidth, overflow: [...globalThis.document.querySelectorAll('body *')].filter(e => e.scrollWidth > e.clientWidth + 1 || e.getBoundingClientRect().right > globalThis.innerWidth + 1).map(e => ({ element: e.tagName, class: e.className, width: Math.round(e.getBoundingClientRect().width), scroll: e.scrollWidth, right: Math.round(e.getBoundingClientRect().right) })).slice(0, 30) }))
  console.log(JSON.stringify(result))
  if (result.document > result.viewport + 1) process.exitCode = 1
} finally { await browser.close() }
