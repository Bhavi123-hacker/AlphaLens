import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Activity, ArrowUpRight, Info, RefreshCw, ShieldCheck } from 'lucide-react'
import { get } from '../api/client'
import { jsonObject, type Stock, type JsonObject } from '../api/contracts'
import { readable } from '../lib/format'
import { setPreferences, usePreferences } from '../lib/preferences'
import { Badge, Empty, EvidenceNote, Heading, Panel, QueryState, StockSearch } from '../components/ui'

function object(value: unknown): JsonObject { return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : {} }
const states = [
  ['WATCH', 'Eligible for monitoring; evidence is insufficient for a stronger setup.'],
  ['SETUP_FORMING', 'Several favorable conditions exist; configured entry requirements are incomplete.'],
  ['ENTRY_SIGNAL', 'Configured evidence passes entry requirements at the decision time. Profit is not guaranteed.'],
  ['HOLD', 'An explicitly evidenced position continues to satisfy holding conditions.'],
  ['TAKE_PROFIT_REVIEW', 'Position evidence calls for a profit/risk review; an exit is not automatic.'],
  ['EXIT_SIGNAL', 'Evidence invalidates configured position continuation conditions.'],
  ['EXITED', 'An actual user-recorded or simulated exit is evidenced; a signal alone cannot establish exit.'],
]
export function Opportunities() {
  const [selected, setSelected] = useState<Stock | null>(null)
  const opportunities = useQuery({ queryKey: ['opportunities'], queryFn: ({ signal }) => get('/opportunities', jsonObject.nullable(), signal) })
  const rankings = useQuery({ queryKey: ['rankings'], queryFn: ({ signal }) => get('/rankings', jsonObject.nullable(), signal) })
  const signals = useQuery({ queryKey: ['signals', selected?.security_id], queryFn: ({ signal }) => get(selected ? `/signals/${encodeURIComponent(selected.security_id)}` : '/signals', jsonObject.nullable(), signal) })
  const explanations = useQuery({ queryKey: ['explanation', selected?.security_id], enabled: !!selected, queryFn: ({ signal }) => get(`/explanations/${encodeURIComponent(selected!.security_id)}`, jsonObject.nullable(), signal) })
  return <><Heading eyebrow="P11–P14 · Evidence-gated decision states" title="Opportunities & signals">Current recommendations require genuine dated evidence.<br />Historical model metrics do not create today's stock picks.</Heading>
    <Panel className="opportunity-empty"><Empty title="Current-session opportunities are unavailable">No verified current-session ranking, risk or signal snapshot is available. P19 daily refresh and inference are not implemented; production signal calibration is not approved.<div className="empty-action"><Link className="button primary" to="/research">Explore historical ML research<ArrowUpRight size={17} /></Link></div></Empty></Panel>
    <div className="three-columns">{[[opportunities, 'Opportunities'], [rankings, 'Rankings'], [signals, 'Signals']].map(([query, title]) => { const q = query as typeof opportunities; return <Panel title={String(title)} key={String(title)}><QueryState query={q}>{q.data && <p>Evidence status: {q.data.evidence_status}</p>}</QueryState></Panel> })}</div>
    <Panel title="Security-specific evidence" subtitle="Read the actual unavailable response; no synthetic substitution"><StockSearch onSelect={setSelected} placeholder="Inspect a security's signal availability" />{selected && <><p>{selected.latest_observed_symbol ?? selected.security_id}</p><QueryState query={explanations}>{explanations.data && <EvidenceNote evidence={explanations.data} />}</QueryState></>}</Panel>
    <Panel title="Decision-state reference" subtitle="Definitions only — these are not active signals"><div className="signal-reference">{states.map(([state, definition], i) => <div key={state}><span className="reference-number">0{i + 1}</span><div><h3>{state}</h3><p>{definition}</p></div></div>)}</div><p className="caption">Each horizon remains independent: 1, 5, 10 and 20 sessions. Position states require position context. Existing development thresholds have not been recalibrated.</p></Panel>
  </>
}
export function DataHealth() {
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => get('/health', jsonObject, signal) })
  const ready = useQuery({ queryKey: ['ready'], queryFn: ({ signal }) => get('/ready', jsonObject, signal), retry: false })
  const status = useQuery({ queryKey: ['system'], queryFn: ({ signal }) => get('/system/status', jsonObject, signal) })
  const freshness = useQuery({ queryKey: ['freshness'], queryFn: ({ signal }) => get('/system/data-freshness', jsonObject, signal) })
  const client = useQueryClient()
  return <><Heading eyebrow="Evidence & component diagnostics" title="Data health">Understand what is connected, unavailable and blocked.<br />Liveness and readiness are separate from production clearance.</Heading>
    <div className="inline-actions right"><button className="button" onClick={() => { for (const key of ['health', 'ready', 'system', 'freshness']) void client.invalidateQueries({ queryKey: [key] }) }}><RefreshCw size={16} />Refresh diagnostic reads</button></div>
    <div className="two-columns"><Panel title="API liveness" actions={<Activity size={18} />}><QueryState query={health}><div className="status-large"><span className="status-dot" />{health.data ? String(health.data.data.backend) : 'Unavailable'}</div><p className="caption">A live process does not imply a ready database or production-approved market data.</p><EvidenceNote evidence={health.data} /></QueryState></Panel>
      <Panel title="Research read readiness" actions={<ShieldCheck size={18} />}><QueryState query={ready}><Badge tone={ready.data?.data.research_read_ready ? 'positive' : 'warning'}>{ready.data?.data.research_read_ready ? 'Required reads ready' : 'Required component unavailable'}</Badge><EvidenceNote evidence={ready.data} /></QueryState></Panel></div>
    <Panel title="Historical data freshness"><QueryState query={freshness}><dl className="detail-grid"><dt>Last evidenced market session</dt><dd>{String(freshness.data?.data.last_evidenced_market_session ?? 'Unavailable')}</dd><dt>Freshness</dt><dd>{String(freshness.data?.data.freshness ?? 'Unavailable')}</dd><dt>Live / intraday data</dt><dd>{String(freshness.data?.data.live_data ?? 'Unavailable')}</dd><dt>Calendar completeness</dt><dd>{String(freshness.data?.data.calendar_completeness ?? 'Unavailable')}</dd></dl><EvidenceNote evidence={freshness.data} /></QueryState></Panel>
    <Panel title="Component availability" subtitle="P17's actual configured read sources"><QueryState query={status}><div className="component-grid">{Object.entries(object(status.data?.data.components)).map(([key, value]) => { const item = object(value); const state = String(item.status ?? 'UNAVAILABLE'); return <div className="component-card" key={key}><span>{readable(key)}</span><Badge tone={['AVAILABLE', 'REACHABLE'].includes(state) ? 'positive' : 'warning'}>{state}</Badge>{typeof item.reason === 'string' && <p>{readable(item.reason)}</p>}{Array.isArray(item.reasons) && <ul>{item.reasons.map((reason) => <li key={String(reason)}>{readable(String(reason))}</li>)}</ul>}</div> })}</div><EvidenceNote evidence={status.data} /></QueryState></Panel>
    <Panel title="Research and deployment restrictions" subtitle="Working software does not clear evidence or security gates"><ul className="restriction-list"><li><Info size={17} /><div><strong>Real historical observations, research-only use</strong><p>Final-vintage revision timing is unknown. Availability is assumed at the next evidenced session; this is not exact historical vendor-view reconstruction.</p></div></li><li><Info size={17} /><div><strong>Benchmark and PIT fundamentals unavailable</strong><p>No fabricated NIFTY series, financial statements or neutral substitute values are displayed.</p></div></li><li><Info size={17} /><div><strong>Models retain insufficient evidence</strong><p>Stored OOS diagnostics and the final holdout do not authorize production promotion or guaranteed returns.</p></div></li><li><ShieldCheck size={17} /><div><strong>Local development only</strong><p>P21 authentication is absent. The approved backend image retains 44 HIGH OS security findings. No public deployment or vulnerability suppression is authorized.</p></div></li></ul></Panel>
  </>
}
export function Settings() {
  const preferences = usePreferences(); const [cleared, setCleared] = useState(false)
  return <><Heading eyebrow="Browser-local presentation preferences" title="Settings">Personalize the workspace without changing research configuration.<br />No data hashes, thresholds or financial records are editable here.</Heading>
    <Panel title="Appearance" subtitle="Preferences are stored in this browser only"><div className="settings-row"><div><h3>Color theme</h3><p>Dark-first research terminal with an accessible light option.</p></div><div className="segmented"><button aria-pressed={preferences.theme === 'dark'} onClick={() => setPreferences({ theme: 'dark' })}>Dark</button><button aria-pressed={preferences.theme === 'light'} onClick={() => setPreferences({ theme: 'light' })}>Light</button></div></div>
      <div className="settings-row"><div><h3>Compact tables</h3><p>Reduce row spacing for larger research comparisons.</p></div><label className="toggle-label"><input type="checkbox" checked={preferences.compact} onChange={(e) => setPreferences({ compact: e.target.checked })} />Enable compact density</label></div>
      <div className="settings-row"><div><h3>Browser-local favorites</h3><p>{preferences.favorites.length} saved identities. These are preferences, not portfolio holdings or server-synchronized records.</p></div><button className="button" disabled={!preferences.favorites.length} onClick={() => { setPreferences({ favorites: [] }); setCleared(true) }}>Clear favorites</button></div>{cleared && <p role="status">Browser favorites cleared.</p>}</Panel>
    <Panel title="Connection & controls"><dl className="detail-grid"><dt>API transport</dt><dd>Same-origin /api/v1 through the loopback Vite proxy</dd><dt>Research access</dt><dd>GET-only persisted reads</dd><dt>Model execution</dt><dd>Disabled</dd><dt>Broker integration</dt><dd>None</dd><dt>Data refresh</dt><dd>Manual read refresh; no P19 ingestion</dd><dt>Reduced motion</dt><dd>Respects the operating-system preference automatically</dd></dl><p className="caption">Backend resource paths and database credentials are configured privately in P17, never through frontend settings.</p><div className="inline-actions"><Link className="button small" to="/data-health">Inspect connection status<ArrowUpRight size={15} /></Link><a className="button small" href="/third-party-notices.txt" target="_blank" rel="noopener noreferrer">Open-source license notices<ArrowUpRight size={15} /></a></div></Panel>
  </>
}
