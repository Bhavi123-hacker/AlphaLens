import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { ArrowUpRight, Activity, BrainCircuit, ShieldCheck } from 'lucide-react'
import { get } from '../api/client'
import { marketResearchSchema } from '../api/nse-market'
import { modelSchema, stockSchema } from '../api/contracts'
import { usePreferences } from '../lib/preferences'
import { Badge, Panel, Stat, QueryState } from '../components/ui'
import { StockWorkspace } from '../components/StockWorkspace'
import { ProviderSearch } from '../components/ProviderWorkspace'
import { UpstoxWatchlist } from '../components/UpstoxWatchlist'
import { DailyResearch } from '../components/DailyResearch'
import { RecentAlerts } from '../components/Notifications'
import { PersonalSummary } from './Personal'

export function Overview() {
  const [selected, setSelected] = useState<string | null>(null); const prefs = usePreferences()
  const stocks = useQuery({ queryKey: ['overview-securities'], queryFn: ({ signal }) => get('/stocks?limit=20', z.array(stockSchema), signal) })
  const models = useQuery({ queryKey: ['models'], queryFn: ({ signal }) => get('/research/models?limit=500', z.array(modelSchema), signal) })
  const candidate = selected ?? prefs.favorites[0]?.security_id ?? stocks.data?.data.find(s => s.analytical_type === 'RESEARCH_EQUITY_CANDIDATE')?.security_id ?? stocks.data?.data[0]?.security_id
  const saved = useQuery({ queryKey: ['overview-saved-research'], retry:false, refetchOnWindowFocus:false, staleTime:60_000, queryFn:({signal})=>get('/nse-market/research?page=1&page_size=5',marketResearchSchema,signal) })
  const evidence=saved.data?.data
  const observed=evidence?.counts.validated_historical_stocks
  const universe=evidence?.counts.verified_eligible_common_equities
  const task=evidence?.operations?.windows_task as Record<string,unknown>|undefined
  const families = new Set(models.data?.data.map(m => m.model_family))
  return <><section className="terminal-hero" aria-label="NSE research command centre"><div><div className="hero-kicker">Private intelligence / NSE equities</div><h1>Your market <em>workspace</em></h1><p className="hero-lede">Observe the market. Interrogate the evidence.</p><p>Genuine source observations, experimental models and portfolio risk in one research terminal. Know what is measured, what failed, and what remains unknown.</p><div className="hero-actions"><Link to="/nse-market" className="button primary">Investigate research candidates <ArrowUpRight size={17}/></Link><Link to="/my-portfolio" className="button">Review portfolio risk</Link></div></div><aside className="hero-instrument" aria-label="Measured research coverage"><Badge tone="neutral">SAVED EOD EVIDENCE</Badge>{saved.isPending&&<p role="status">Reading saved research coverage...</p>}{saved.isError&&<p role="status">Saved coverage could not be read. <button className="button small" onClick={()=>void saved.refetch()}>Retry saved evidence</button></p>}<strong>{observed?.toLocaleString()??'—'} <small>/ {universe?.toLocaleString()??'unmeasured'}</small></strong><p>Observed securities / verified current common-equity identities. Discovery is not complete market coverage.</p>{typeof observed==='number'&&typeof universe==='number'&&universe>0&&<meter aria-label="Retained historical coverage" min={0} max={universe} value={observed}/>}<footer><span>Last retained session<br/><strong>{String(evidence?.coverage?.end??'Not observed')}</strong></span><span>Accepted rankings<br/><strong>{evidence?.accepted_current_rankings??'Not observed'}</strong></span></footer><Link to="/nse-market#daily-research">Inspect saved collection status <ArrowUpRight size={14}/></Link></aside></section>
    <ProviderSearch onSelect={i => setSelected(i.canonical_security_id || 'upstox:' + i.provider_key)} />
    {candidate ? <StockWorkspace key={candidate} securityId={candidate} compact /> : <Panel title="Open a stock workspace"><QueryState query={stocks}><p>Find a positively verified NSE equity above, or select an independent archive identity in Market Explorer.</p></QueryState></Panel>}
    <div className="personal-shortcuts"><Link to="/decision-desk"><strong>Research Decision Desk</strong><span>Entry conditions, holding reviews and hypothetical exit scenarios</span></Link><Link to="/opportunities"><strong>Historical winners</strong><span>Exact dates, coverage and exclusions</span></Link></div><PersonalSummary/><UpstoxWatchlist />
    <div className="research-summary"><div><BrainCircuit size={23} /><h2>Historical research</h2><p>Completed experiments, unchanged methodology. Experimental scores are separate from independently accepted predictions.</p></div><Link className="button" to="/research">Open ML research <ArrowUpRight size={16} /></Link></div>
    <div className="stats-grid"><Stat label="Stored model fits" value={models.data?.page?.total ?? 'Unavailable'} note="Read-only completed research" /><Stat label="Model families" value={models.isSuccess ? families.size : 'Unavailable'} note="Existing chronological evaluations" /><Stat label="Accepted current rankings" value={evidence?.accepted_current_rankings??"Not observed"} note="Experimental scores remain unvalidated" /><Stat label="Last observed collecting task" value={String(task?.state??"Not observed")} note="Windows state is not verified data capture" /></div>
    <div className="three-columns"><Link className="shortcut-card" to="/intelligence"><BrainCircuit /><h3>Research intelligence</h3><p>Descriptive regimes, reliability and drift with explicit evidence boundaries.</p><span>Explore intelligence <ArrowUpRight size={16} /></span></Link><Link className="shortcut-card" to="/backtests"><Activity /><h3>Backtest evidence</h3><p>504 frozen hypothetical runs; unresolved economics stay visible.</p><span>Inspect historical outcomes <ArrowUpRight size={16} /></span></Link><Link className="shortcut-card" to="/data-health"><ShieldCheck /><h3>Sources & system health</h3><p>Provider access, research automation and production readiness are separate.</p><span>Inspect diagnostics <ArrowUpRight size={16} /></span></Link></div>
    <details className="automation-diagnostics"><summary>Research automation diagnostics · retained ingestion and inference restrictions</summary><DailyResearch /></details><RecentAlerts />
  </>
}
