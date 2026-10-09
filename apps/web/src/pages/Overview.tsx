import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { ArrowUpRight, Layers3, FlaskConical, ShieldCheck, Activity } from 'lucide-react'
import { get } from '../api/client'
import { comparisonSchema, jsonObject, modelSchema, stockSchema, type Stock } from '../api/contracts'
import { readable } from '../lib/format'
import { Badge, Heading, Panel, QueryState, Stat, StockSearch, ErrorState } from '../components/ui'
import { StockWorkspace } from '../components/StockWorkspace'

export function Overview() {
  const [selected, setSelected] = useState<Stock | null>(null)
  const stocks = useQuery({ queryKey: ['overview-securities'], queryFn: ({ signal }) => get('/stocks?limit=20', z.array(stockSchema), signal) })
  const models = useQuery({ queryKey: ['models'], queryFn: ({ signal }) => get('/research/models?limit=500', z.array(modelSchema), signal) })
  const freshness = useQuery({ queryKey: ['freshness'], queryFn: ({ signal }) => get('/system/data-freshness', jsonObject, signal) })
  const status = useQuery({ queryKey: ['system'], queryFn: ({ signal }) => get('/system/status', jsonObject, signal) })
  const evaluation = useQuery({ queryKey: ['evaluation'], queryFn: ({ signal }) => get('/research/evaluation', comparisonSchema, signal) })
  const portfolio = useQuery({ queryKey: ['portfolios'], queryFn: ({ signal }) => get('/portfolios?limit=5', z.array(jsonObject), signal) })
  const candidate = selected ?? stocks.data?.data.find((stock) => stock.analytical_type === 'RESEARCH_EQUITY_CANDIDATE') ?? stocks.data?.data[0]
  const families = new Set(models.data?.data.map((model) => model.model_family))
  const horizons = [...new Set(models.data?.data.map((model) => model.horizon))].sort((a, b) => a - b)
  return <><Heading eyebrow="NSE · Historical research platform" title="Research overview">A clear view of market evidence.<br />Explore history. Understand uncertainty.</Heading>
    <div className="overview-hero"><div><Badge tone="accent"><FlaskConical size={12} />REAL OBSERVATIONS · RESEARCH USE</Badge><h2>Intelligence grounded<br />in observed history.</h2><p>Investigate prices, technical context and chronological model evaluations. Every result retains its source and limitations.</p><Link className="button primary" to="/market">Explore securities<ArrowUpRight size={17} /></Link></div><div className="hero-evidence"><span className="caption">LATEST EVIDENCED SESSION</span><strong>{String(freshness.data?.data.last_evidenced_market_session ?? 'Unavailable')}</strong><div><span className="status-dot" />Historical EOD archive</div><p>Final-vintage assumptions<br />Production data: not cleared</p><Link to="/data-health">Inspect evidence status <ArrowUpRight size={15} /></Link></div></div>
    <div className="stats-grid"><Stat label="Stored model fits" value={models.data?.page?.total ?? 'Unavailable'} note="Read-only completed research" /><Stat label="Model families" value={models.isSuccess ? families.size : 'Unavailable'} note={models.isSuccess ? [...families].map(readable).slice(0, 3).join(' · ') + '…' : 'Awaiting verified API'} /><Stat label="Prediction horizons" value={horizons.length ? horizons.map((h) => `${h}D`).join(' / ') : 'Unavailable'} note="Trading sessions, not calendar days" /><Stat label="Production readiness" value="Blocked" tone="warning-text" note="Data, economics and security gates remain open" /></div>
    <div className="overview-grid"><div><div className="section-label"><h2>Historical price workspace</h2><StockSearch compact onSelect={setSelected} placeholder="Choose a historical security" /></div>
      {candidate ? <StockWorkspace securityId={candidate.security_id} compact /> : <Panel><QueryState query={stocks}><p>No observed security is available.</p></QueryState></Panel>}</div>
      <div className="overview-aside"><Panel title="Research candidates" subtitle="Existing selections; no production promotion"><QueryState query={evaluation}>{evaluation.data && Object.entries(evaluation.data.data.selected).sort(([a], [b]) => Number(a) - Number(b)).map(([horizon, value]) => <Link className="candidate-row" key={horizon} to={`/research?horizon=${horizon}`}><span className="horizon-tag">{horizon}D</span><div><strong>{readable(String(value.model_family))}</strong><span className="cell-secondary">Insufficient evidence</span></div><ArrowUpRight size={15} /></Link>)}</QueryState><div className="aside-note"><ShieldCheck size={16} /><p>Positive rank IC does not establish profitable trading.</p></div></Panel>
        <Panel title="Portfolio records" subtitle="Read-only P15 accounting">{portfolio.isError ? <div className="compact-unavailable"><Activity size={18} /><p>Portfolio database unavailable.<br /><Link to="/portfolios">View connection details</Link></p></div> : portfolio.isPending ? <p className="caption">Checking saved records…</p> : <><strong>{portfolio.data?.data.length ?? 0} records in this page</strong><p className="caption">{portfolio.data?.data.length ? 'Open the workspace to inspect evidenced holdings.' : 'No portfolios are recorded in the connected database.'}</p><Link className="button small" to="/portfolios">Open portfolios<ArrowUpRight size={14} /></Link></>}</Panel>
      </div></div>
    <div className="three-columns"><Link className="shortcut-card" to="/research"><FlaskConical /><h3>ML research lab</h3><p>Compare real OOS metrics, fold stability and the isolated final holdout.</p><span>Inspect models<ArrowUpRight size={16} /></span></Link><Link className="shortcut-card" to="/backtests"><Layers3 /><h3>Backtest evidence</h3><p>Separate closed-trade diagnostics from unresolved full-path economics.</p><span>Review outcomes<ArrowUpRight size={16} /></span></Link><Link className="shortcut-card" to="/data-health"><ShieldCheck /><h3>Data health</h3><p>Inspect connected sources, missing evidence and research restrictions.</p><span>Check sources<ArrowUpRight size={16} /></span></Link></div>
    {freshness.isError && <ErrorState error={freshness.error} retry={() => void freshness.refetch()} />}{status.isError && <ErrorState error={status.error} />}
  </>
}
