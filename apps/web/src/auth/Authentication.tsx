import { createContext, useCallback, useContext, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, LockKeyhole, LogOut, ShieldCheck } from 'lucide-react'
import { z } from 'zod'
import { APIError, authRequest, setSessionContext } from '../api/client'
import { usePreferences } from '../lib/preferences'

const identity = z.object({ account_id: z.string(), username: z.string(), role: z.literal('ADMIN'), session_id: z.string(), csrf_token: z.string(), absolute_expires: z.number(), idle_seconds: z.number() })
type Identity = Omit<z.infer<typeof identity>, 'csrf_token'>
type Access = { user: Identity; logout: () => Promise<void>; invalidate: () => void }
const Context = createContext<Access | null>(null)
function errorText(error: unknown) { return error instanceof APIError ? error.message : 'The local account service is unavailable. Check the backend and retry.' }
function safePath(path: string) { return path.startsWith('/') && !path.startsWith('//') && !path.includes('\\') && path !== '/login' ? path : '/' }

export function Authentication({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Identity | null>(null); const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState(''); const query = useQueryClient(); const location = useLocation(); const navigate = useNavigate()
  const preferences = usePreferences()
  const accept = useCallback((value: z.infer<typeof identity>) => { const { csrf_token, ...account } = value; setSessionContext(csrf_token); setUser(account) }, [])
  const invalidate = useCallback((announce = true) => {
    if (announce && user && typeof BroadcastChannel !== 'undefined') { const channel = new BroadcastChannel('alphalens-session'); channel.postMessage({ event: 'SESSION_ENDED', session_id: user.session_id }); channel.close() }
    setSessionContext(); setUser(null); void query.cancelQueries().then(() => query.clear()); setMessage('Your session ended. Sign in to continue.'); navigate('/login', { replace: true, state: { returnTo: safePath(location.pathname) } })
  }, [location.pathname, navigate, query, user])
  useEffect(() => { document.documentElement.dataset.theme = preferences.theme }, [preferences.theme])
  useEffect(() => {
    let live = true
    authRequest('/auth/session', identity).then((value) => { if (live) accept(value) }).catch((error: unknown) => { if (live) setMessage(error instanceof APIError && error.status === 401 ? '' : errorText(error)) }).finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [accept])
  useEffect(() => { const ended = () => invalidate(); window.addEventListener('alphalens:session-expired', ended); return () => window.removeEventListener('alphalens:session-expired', ended) }, [invalidate])
  useEffect(() => {
    if (!user || typeof BroadcastChannel === 'undefined') return
    const channel = new BroadcastChannel('alphalens-session')
    channel.onmessage = (event: MessageEvent<unknown>) => { const value = z.object({ event: z.literal('SESSION_ENDED'), session_id: z.string() }).safeParse(event.data); if (value.success && value.data.session_id === user.session_id) invalidate(false) }
    return () => channel.close()
  }, [user, invalidate])
  useEffect(() => {
    if (!user) return
    let deadline = 0; let timer: ReturnType<typeof setTimeout>
    const check = () => { if (Date.now() >= deadline) invalidate() }
    const refresh = () => { clearTimeout(timer); deadline = Math.min(Date.now() + user.idle_seconds * 1000, user.absolute_expires * 1000); timer = setTimeout(check, Math.max(0, deadline - Date.now())) }
    refresh(); window.addEventListener('alphalens:authenticated-read', refresh); window.addEventListener('focus', check)
    return () => { clearTimeout(timer); window.removeEventListener('alphalens:authenticated-read', refresh); window.removeEventListener('focus', check) }
  }, [user, invalidate])
  useEffect(() => { if (!loading && !user && location.pathname !== '/login') navigate('/login', { replace: true, state: { returnTo: safePath(location.pathname) } }) }, [loading, user, location.pathname, navigate])
  async function login(name: string, password: string) {
    const value = await authRequest('/auth/login', identity, { username: name, password })
    await query.cancelQueries(); query.clear(); accept(value); setMessage('')
    const state = location.state as { returnTo?: string } | null
    navigate(safePath(state?.returnTo ?? '/'), { replace: true })
  }
  async function logout() { await authRequest('/auth/logout', z.object({ status: z.literal('LOGGED_OUT') }), {}); invalidate() }
  if (loading) return <div className="auth-page" role="status">Checking local session…</div>
  if (!user || location.pathname === '/login') return <Login login={login} initialMessage={message} />
  return <Context.Provider value={{ user, logout, invalidate }}>{children}</Context.Provider>
}

function Login({ login, initialMessage }: { login: (name: string, password: string) => Promise<void>; initialMessage: string }) {
  const [name, setName] = useState(''); const [password, setPassword] = useState(''); const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(''); try { await login(name, password) } catch (e) { setError(errorText(e)); setPassword('') } finally { setBusy(false) } }
  return <main className="auth-page"><section className="auth-card"><div className="auth-brand">Alpha<span>Lens</span></div><div className="eyebrow">LOCAL RESEARCH WORKSPACE</div><LockKeyhole size={30} /><h1>Sign in</h1><p>Access your preserved research, portfolios and notifications.</p>
    <form onSubmit={(e) => void submit(e)}><label>Username<input autoComplete="username" autoFocus required maxLength={32} value={name} onChange={(e) => setName(e.target.value)} /></label><label>Password<div className="password-input"><input type={show ? 'text' : 'password'} autoComplete="current-password" required maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} /><button type="button" className="icon-button" aria-label={show ? 'Hide password' : 'Show password'} aria-pressed={show} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label>
      {(error || initialMessage) && <p role="alert">{error || initialMessage}</p>}<button className="button auth-submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form>
    <div className="auth-notice"><ShieldCheck size={16} /><span>Single local operator. Research only. HTTP loopback has no TLS protection.</span></div><p className="caption">Initial setup and recovery use the protected local CLI. No public sign-up or email reset.</p></section></main>
}

const sessionsSchema = z.object({ sessions: z.array(z.object({ session_id: z.string(), created_at: z.number(), last_seen: z.number(), absolute_expires: z.number(), revoked_at: z.number().nullable(), active: z.boolean() })) })
export function AccountSettings() {
  const account = useContext(Context); const [current, setCurrent] = useState(''); const [replacement, setReplacement] = useState(''); const [confirmation, setConfirmation] = useState('')
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false); const [sessions, setSessions] = useState<z.infer<typeof sessionsSchema>['sessions']>([])
  if (!account) return null
  async function action(work: () => Promise<unknown>) { setBusy(true); setMessage(''); try { await work() } catch (e) { setMessage(errorText(e)) } finally { setBusy(false) } }
  async function change(event: FormEvent) { event.preventDefault(); if (replacement !== confirmation) { setMessage('New passwords must match.'); return } await action(async () => { await authRequest('/auth/password', z.object({ status: z.string() }), { current_password: current, new_password: replacement }); setCurrent(''); setReplacement(''); setConfirmation(''); account!.invalidate() }) }
  return <section className="panel"><h2>Account security</h2><p className="caption">{account.user.username} · Administrator · Single-operator workspace</p><p>Session expires after 30 idle minutes or at {new Date(account.user.absolute_expires * 1000).toLocaleString()}.</p>
    <form className="auth-password-form" onSubmit={(e) => void change(e)}><label>Current password<input type="password" required autoComplete="current-password" value={current} maxLength={128} onChange={(e) => setCurrent(e.target.value)} /></label><label>New password<input type="password" required autoComplete="new-password" minLength={15} maxLength={128} value={replacement} onChange={(e) => setReplacement(e.target.value)} /></label><label>Confirm new password<input type="password" required autoComplete="new-password" minLength={15} maxLength={128} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} /></label><p className="caption">Use 15–128 characters, avoid your username and repeated/common passwords. Changing it revokes every session.</p><button className="button" disabled={busy}>Change password</button></form>
    <div className="inline-actions"><button className="button" disabled={busy} onClick={() => void action(account.logout)}><LogOut size={16} />Log out</button><button className="button" disabled={busy} onClick={() => void action(async () => setSessions((await authRequest('/auth/sessions', sessionsSchema)).sessions))}>Inspect sessions</button></div>
    {message && <p role="alert">{message}</p>}<ul className="session-list">{sessions.map((s) => <li key={s.session_id}><span>{s.session_id === account.user.session_id ? 'Current session' : 'Other local session'} · {s.revoked_at ? 'Revoked' : s.active ? 'Active' : 'Expired'}</span><button className="button small" disabled={busy || s.revoked_at !== null} onClick={() => void action(async () => { await authRequest('/auth/sessions/revoke', z.object({ status: z.string() }), { session_id: s.session_id }); if (s.session_id === account.user.session_id) account.invalidate(); else setSessions((await authRequest('/auth/sessions', sessionsSchema)).sessions) })}>Revoke session</button></li>)}</ul>
    <p className="caption">Cookie-based local authentication. HTTP loopback, public networking and multi-owner isolation are separate security boundaries. Financial execution remains disabled.</p></section>
}
