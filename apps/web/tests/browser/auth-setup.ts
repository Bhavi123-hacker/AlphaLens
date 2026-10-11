import { chromium, expect, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'

// Isolated TEST_ONLY identity, supplied outside Git. No fabricated market responses.
export function credentials(): { username: string; password: string } {
  if (!process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE) throw new Error('Provide an isolated TEST_ONLY credential file')
  return JSON.parse(readFileSync(process.env.ALPHALENS_BROWSER_CREDENTIAL_FILE, 'utf8')) as { username: string; password: string }
}
export async function signIn(page: Page) {
  const value = credentials()
  await page.getByLabel('Username', { exact: true }).fill(value.username)
  await page.getByLabel('Password', { exact: true }).fill(value.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toHaveCount(0)
}
export default async function setup() {
  const browser = await chromium.launch({ channel: 'chromium' })
  try {
    const page = await browser.newPage()
    await page.goto(`${process.env.ALPHALENS_BROWSER_BASE_URL ?? 'http://127.0.0.1:5173'}/login`)
    await signIn(page)
    if (!process.env.ALPHALENS_BROWSER_STATE_FILE) throw new Error('Provide a protected D-drive state location')
    await page.context().storageState({ path: process.env.ALPHALENS_BROWSER_STATE_FILE })
  } finally { await browser.close() }
}
