import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { z } from 'zod'
import { AccountSettings, Authentication } from '../src/auth/Authentication'
import { APIError, authRequest, get, setSessionContext } from '../src/api/client'

const TEST_ONLY = { account_id: 'TEST_ONLY_ACCOUNT', username: 'test_operator', role: 'ADMIN', session_id: 'TEST_ONLY_SESSION', csrf_token: 'TEST_ONLY_CSRF', absolute_expires: 4102444800, idle_seconds: 1800 }
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status })
function setup(path = '/research') {
  const query = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={query}><MemoryRouter initialEntries={[path]}><Authentication><h1>Private research</h1><AccountSettings /></Authentication></MemoryRouter></QueryClientProvider>)
  return query
}
afterEach(() => { vi.unstubAllGlobals(); setSessionContext(); localStorage.clear() })
describe('TEST_ONLY authentication contracts', () => {
  it('protects navigation until an actual session response succeeds', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ error_code: 'AUTHENTICATION_REQUIRED' }, 401)))
    setup(); expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByText('Private research')).not.toBeInTheDocument()
    expect(screen.queryByText('Account security')).not.toBeInTheDocument()
  })
  it('login supports keyboard and password visibility with safe error handling', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({}, 401)))
    setup(); await screen.findByRole('heading', { name: 'Sign in' })
    const user = userEvent.setup(); await user.type(screen.getByLabelText('Username'), 'test_operator')
    await user.type(screen.getByLabelText('Password'), 'TEST_ONLY entered value')
    await user.click(screen.getByRole('button', { name: 'Show password' })); expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text')
    await user.click(screen.getByRole('button', { name: 'Hide password' })); screen.getByLabelText('Password').focus(); await user.keyboard('{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in failed')
    expect(screen.getByLabelText('Password')).toHaveValue('')
  })
  it('restores a genuine session and clears private cache after server logout', async () => {
    const fetcher = vi.fn().mockImplementation(async (url: string) => response(url.endsWith('/logout') ? { status: 'LOGGED_OUT' } : TEST_ONLY))
    vi.stubGlobal('fetch', fetcher)
    const query = setup('/settings'); await screen.findByText('Private research')
    query.setQueryData(['private_portfolio'], { PRIVATE_TEST_ONLY_RECORD: true })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Log out' }))
    await screen.findByRole('heading', { name: 'Sign in' })
    await waitFor(() => expect(query.getQueryData(['private_portfolio'])).toBeUndefined())
    const call = fetcher.mock.calls.find((c: unknown[]) => String(c[0]).endsWith('/logout'))
    expect(call?.[1]).toMatchObject({ credentials: 'same-origin', method: 'POST', headers: { 'X-CSRF-Token': 'TEST_ONLY_CSRF' } })
    expect(localStorage.getItem('csrf_token')).toBeNull(); expect(localStorage.getItem('session')).toBeNull()
  })
  it('expired sessions remove private UI and caches', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(TEST_ONLY)))
    const query = setup(); await screen.findByText('Private research'); query.setQueryData(['private_model'], { private: true })
    window.dispatchEvent(new Event('alphalens:session-expired'))
    await screen.findByRole('heading', { name: 'Sign in' })
    expect(screen.getByRole('alert')).toHaveTextContent('Your session ended')
    await waitFor(() => expect(query.getQueryData(['private_model'])).toBeUndefined())
  })
  it('a 503 authentication store failure is visible and never becomes a login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({}, 503)))
    setup(); await screen.findByRole('heading', { name: 'Sign in' })
    expect(screen.getByRole('alert')).toHaveTextContent('security request was rejected')
    expect(screen.queryByText('Private research')).not.toBeInTheDocument()
  })
  it('late private responses from an old session cannot populate the new workspace', async () => {
    let finish: ((r: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise<Response>((resolve) => { finish = resolve })))
    const request = get('/portfolios', z.array(z.unknown()))
    await waitFor(() => expect(finish).toBeDefined())
    setSessionContext('TEST_ONLY_OTHER_SESSION_CSRF')
    finish?.(response({ data: [{ private: true }] }))
    await expect(request).rejects.toMatchObject({ status: 401, code: 'SESSION_CHANGED' })
  })
  it('central auth transport rejects external/unknown routes and never swallows forbidden responses', async () => {
    await expect(authRequest('https://malicious.invalid', z.unknown())).rejects.toBeInstanceOf(APIError)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({}, 403)))
    await expect(authRequest('/auth/password', z.unknown(), {})).rejects.toMatchObject({ status: 403 })
  })
})
