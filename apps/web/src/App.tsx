import { QuickPalette, WatchlistRail } from './components/TerminalChrome'
import { ProviderAutocomplete } from './components/ProviderAutocomplete'
import { Suspense, lazy, useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeftToLine, ArrowRightFromLine, FlaskConical, Menu, ShieldCheck, X, Moon, Sun } from 'lucide-react'
import { navigation } from './lib/navigation'
import { get } from './api/client'
import { jsonObject } from './api/contracts'
import { Badge } from './components/ui'
import { setPreferences, usePreferences } from './lib/preferences'
import { NotificationBell, Notifications } from './components/Notifications'
import { Authentication } from './auth/Authentication'
import { PageBoundary } from './components/PageBoundary'
const Overview = lazy(() => import('./pages/Overview').then((m) => ({ default: m.Overview })))
const Explorer = lazy(() => import('./pages/Market').then((m) => ({ default: m.Explorer })))
const Analysis = lazy(() => import('./pages/Market').then((m) => ({ default: m.Analysis })))
const Research = lazy(() => import('./pages/Research').then((m) => ({ default: m.Research })))
const NseMarket = lazy(() => import('./pages/NseMarket').then((m) => ({ default: m.NseMarket })))
const ExperimentalResearchV2 = lazy(() => import('./pages/ExperimentalV2').then((m) => ({ default: m.ExperimentalResearchV2 })))
const ExperimentalResearch = lazy(() => import('./pages/Experimental').then((m) => ({ default: m.ExperimentalResearch })))
const Backtests = lazy(() => import('./pages/Backtests').then((m) => ({ default: m.Backtests })))
const Portfolios = lazy(() => import('./pages/Accounts').then((m) => ({ default: m.Portfolios })))
const Paper = lazy(() => import('./pages/Accounts').then((m) => ({ default: m.Paper })))
const Opportunities = lazy(() => import('./pages/Opportunities').then((m) => ({ default: m.ExploreOpportunities })))
const MyPortfolio = lazy(() => import('./pages/Personal').then(m=>({default:m.MyPortfolio})))
const ResearchPreferences = lazy(() => import('./pages/Personal').then(m=>({default:m.ResearchPreferences})))
const Journal = lazy(() => import('./pages/Personal').then(m=>({default:m.ResearchJournal})))
const Watchlists = lazy(() => import('./pages/Watchlists').then(m=>({default:m.NamedWatchlists})))
const DecisionDesk = lazy(()=>import('./pages/DecisionDesk').then(m=>({default:m.DecisionDesk})))
const Copilot = lazy(() => import('./pages/Opportunities').then(m=>({default:m.ResearchCopilot})))
const ResearchAlerts = lazy(() => import('./pages/Opportunities').then(m=>({default:m.ResearchAlertRules})))
const DataHealth = lazy(() => import('./pages/Status').then((m) => ({ default: m.DataHealth })))
const Settings = lazy(() => import('./pages/Status').then((m) => ({ default: m.Settings })))
const Heatmap = lazy(() => import('./pages/Discovery').then(m => ({ default: m.Heatmap })))
const Comparison = lazy(() => import('./pages/Comparison').then(m => ({ default: m.Comparison })))
const Intelligence = lazy(() => import('./pages/Intelligence').then(m => ({ default: m.Intelligence })))
export function App() { return <Authentication><Workspace /></Authentication> }
function Workspace() {
  const [collapsed, setCollapsed] = useState(true); const [mobile, setMobile] = useState(false)
  const preferences = usePreferences(); const location = useLocation()
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => get('/health', jsonObject, signal), staleTime: 30_000 })
  const freshness = useQuery({ queryKey: ['freshness'], queryFn: ({ signal }) => get('/system/data-freshness', jsonObject, signal) })
  useEffect(() => { document.documentElement.dataset.theme = preferences.theme; document.documentElement.dataset.compact = String(preferences.compact) }, [preferences.theme, preferences.compact])
  useEffect(() => { document.title = `AlphaLens · ${navigation.find(([path]) => path === location.pathname)?.[1] ?? 'Stock analysis'}` }, [location.pathname])
  const title = navigation.find(([path]) => path === location.pathname)?.[1] ?? 'Stock analysis'
  return <div className={`app ${collapsed ? 'sidebar-collapsed' : ''} ${mobile ? 'mobile-nav-open' : ''}`}><a className="skip-link" href="#main-content">Skip to content</a>
    {mobile && <button className="nav-backdrop" aria-label="Close navigation" onClick={() => setMobile(false)} />}
    <aside className="sidebar" aria-label="Primary navigation"><NavLink to="/" className="brand" aria-label="AlphaLens overview" onClick={() => setMobile(false)}><span className="brand-mark">α</span><span className="brand-name">Alpha<span>Lens</span><small>RESEARCH INTELLIGENCE</small></span></NavLink>
      <div className="sidebar-label">WORKSPACE</div><nav>{navigation.map(([path, label, Icon]) => <NavLink key={path} to={path} end={path === '/'} title={collapsed ? label : undefined} onClick={() => setMobile(false)}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-bottom"><div className="local-mode"><ShieldCheck size={17} /><div>Local research workspace<span>No live trading · no execution</span></div></div><button className="collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>{collapsed ? <ArrowRightFromLine size={17} /> : <ArrowLeftToLine size={17} />}<span>Collapse sidebar</span></button></div>
      <button className="mobile-close icon-button" aria-label="Close navigation" onClick={() => setMobile(false)}><X /></button></aside>
    <div className="app-body"><header className="topbar"><div className="topbar-title"><button className="mobile-toggle icon-button" aria-label="Open navigation" onClick={() => setMobile(true)}><Menu /></button><span className="breadcrumb">Workspace<span>/</span><strong>{title}</strong></span></div>
      <ProviderAutocomplete/>
      <div className="topbar-status"><QuickPalette /><NotificationBell /><span className={`connection ${health.isSuccess ? 'connected' : ''}`} title={health.isSuccess ? 'P17 is alive; readiness is evaluated separately' : 'Local P17 connection unavailable'}><span className="status-dot" />{health.isSuccess ? 'API connected' : health.isPending ? 'Connecting' : 'API offline'}</span><button className="icon-button" aria-label={preferences.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'} onClick={() => setPreferences({ theme: preferences.theme === 'dark' ? 'light' : 'dark' })}>{preferences.theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</button></div></header>
      <div className="research-bar"><div><FlaskConical size={14} /><strong>Research only</strong><span>Final-vintage archive · not production-cleared</span></div><span className="evidence-date">Archive through {String(freshness.data?.data.last_evidenced_market_session ?? 'unavailable')}</span></div>
      <div className="market-source-strip" aria-label="Market source strip"><span><span className="status-dot" />NSE Equity <strong>Upstox · explicit private snapshots</strong></span><span>Research archive <strong>{String(freshness.data?.data.last_evidenced_market_session ?? 'Unavailable')}</strong></span><span>Indices <strong>Verified series unavailable</strong></span></div>
      {freshness.data?.classification.data_reality === 'TEST_ONLY' && <div className="demo-banner" role="status">TEST_ONLY DEMONSTRATION - Synthetic evidence. No real prices, forecasts or market performance.</div>}
      <div className="terminal-body"><WatchlistRail /><main id="main-content" tabIndex={-1} key={location.pathname}><PageBoundary><Suspense fallback={<div className="skeleton-block" role="status" aria-label="Loading page"><span /><span /></div>}><Routes>
        <Route path="/" element={<Overview />} /><Route path="/heatmap" element={<Heatmap />} /><Route path="/screener" element={<Heatmap screener />} /><Route path="/compare" element={<Comparison />} /><Route path="/market" element={<Explorer />} /><Route path="/analysis" element={<Analysis />} /><Route path="/stocks/:security_id" element={<Analysis />} /><Route path="/intelligence" element={<Intelligence />} /><Route path="/research" element={<Research />} /><Route path="/experimental-ai" element={<ExperimentalResearch />} /><Route path="/nse-market" element={<NseMarket />} /><Route path="/experimental-ai-v2" element={<ExperimentalResearchV2 />} /><Route path="/opportunities" element={<Opportunities />} /><Route path="/portfolios" element={<Portfolios />} /><Route path="/my-portfolio" element={<MyPortfolio/>}/><Route path="/preferences" element={<ResearchPreferences/>}/><Route path="/watchlists" element={<Watchlists/>}/><Route path="/journal" element={<Journal/>}/><Route path="/decision-desk" element={<DecisionDesk/>}/><Route path="/copilot" element={<Copilot/>}/><Route path="/research-alerts" element={<ResearchAlerts/>}/><Route path="/paper" element={<Paper />} /><Route path="/backtests" element={<Backtests />} /><Route path="/data-health" element={<DataHealth />} /><Route path="/notifications" element={<Notifications />} /><Route path="/settings" element={<Settings />} /><Route path="*" element={<div className="empty-state"><h1>Page not found</h1><NavLink to="/">Return to overview</NavLink></div>} />
      </Routes></Suspense></PageBoundary></main></div><footer className="app-footer"><span>AlphaLens · Historical NSE research</span><Badge tone="warning">Decision support only</Badge><span>Not investment advice. No guaranteed returns.</span></footer></div></div>
}
