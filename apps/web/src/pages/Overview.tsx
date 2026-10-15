import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { ArrowUpRight, Activity, BrainCircuit, ShieldCheck } from 'lucide-react'
import { get } from '../api/client'
import { modelSchema, stockSchema } from '../api/contracts'
import { usePreferences } from '../lib/preferences'
import { Heading, Panel, Stat, QueryState } from '../components/ui'
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
  const families = new Set(models.data?.data.map(m => m.model_family))
  return <><Heading eyebrow="Private NSE market research" title="Your market workspace">Price, source and time in focus. Provider snapshots stay separate from frozen research.</Heading>
    <ProviderSearch onSelect={i => setSelected(i.canonical_security_id || 'upstox:' + i.provider_key)} />
    {candidate ? <StockWorkspace key={candidate} securityId={candidate} compact /> : <Panel title="Open a stock workspace"><QueryState query={stocks}><p>Find a positively verified NSE equity above, or select an independent archive identity in Market Explorer.</p></QueryState></Panel>}
    <div className="personal-shortcuts"><Link to="/decision-desk"><strong>Research Decision Desk</strong><span>Entry conditions, holding reviews and hypothetical exit scenarios</span></Link><Link to="/opportunities"><strong>Historical winners</strong><span>Exact dates, coverage and exclusions</span></Link></div><PersonalSummary/><UpstoxWatchlist />
    <div className="research-summary"><div><BrainCircuit size={23} /><h2>Historical research</h2><p>Completed experiments, unchanged methodology. No current stock predictions.</p></div><Link className="button" to="/research">Open ML research <ArrowUpRight size={16} /></Link></div>
    <div className="stats-grid"><Stat label="Stored model fits" value={models.data?.page?.total ?? 'Unavailable'} note="Read-only completed research" /><Stat label="Model families" value={models.isSuccess ? families.size : 'Unavailable'} note="Existing chronological evaluations" /><Stat label="Current ML inference" value="Unavailable" note="Independent model and input gates" /><Stat label="Retained automation" value="Disabled" note="Transient market data is separate" /></div>
    <div className="three-columns"><Link className="shortcut-card" to="/intelligence"><BrainCircuit /><h3>Research intelligence</h3><p>Descriptive regimes, reliability and drift with explicit evidence boundaries.</p><span>Explore intelligence <ArrowUpRight size={16} /></span></Link><Link className="shortcut-card" to="/backtests"><Activity /><h3>Backtest evidence</h3><p>504 frozen hypothetical runs; unresolved economics stay visible.</p><span>Inspect historical outcomes <ArrowUpRight size={16} /></span></Link><Link className="shortcut-card" to="/data-health"><ShieldCheck /><h3>Sources & system health</h3><p>Provider access, research automation and production readiness are separate.</p><span>Inspect diagnostics <ArrowUpRight size={16} /></span></Link></div>
    <details className="automation-diagnostics"><summary>Research automation diagnostics · retained ingestion and inference restrictions</summary><DailyResearch /></details><RecentAlerts />
  </>
}
