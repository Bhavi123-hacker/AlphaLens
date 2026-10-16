import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { get } from '../api/client'
import { dailyRunSchema, dailyStatusSchema } from '../api/daily'
import { readable } from '../lib/format'
import { Badge, EvidenceNote, Panel, QueryState } from './ui'
import { ProspectiveResearch } from './ProspectiveResearch'

export function DailyResearch({ timeline = false }: { timeline?: boolean }) {
  const collection=useQuery({queryKey:['private-eod-status'],retry:false,queryFn:({signal})=>get('/providers/private-eod-status',z.object({configured:z.boolean(),selected_count:z.number(),observations:z.number(),latest_session:z.string().nullable(),scheduler_enabled:z.boolean(),task:z.object({schedule:z.string().nullable()}).nullable(),inference:z.string()}),signal)})
  const status = useQuery({ queryKey: ['daily-status'], queryFn: ({ signal }) => get('/daily/status', dailyStatusSchema, signal) })
  const runs = useQuery({ queryKey: ['daily-runs'], enabled: timeline, queryFn: ({ signal }) => get('/daily/runs?limit=20', z.array(dailyRunSchema), signal) })
  const item = status.data?.data
  return <>{collection.data?.data.configured&&<Panel title="Private selected-watchlist EOD collection" subtitle="Independent session/date/source gates; model acceptance is separate"><div className="inline-actions"><Badge tone="positive">{collection.data.data.observations} retained observations</Badge><Badge tone={collection.data.data.scheduler_enabled?'positive':'warning'}>{collection.data.data.scheduler_enabled?'Daily task activated':'Daily task inactive'}</Badge></div><p>{collection.data.data.selected_count} explicitly selected instruments; latest captured session {collection.data.data.latest_session??'pending'}. Coverage is this observed cohort, not the entire NSE.</p><p>{collection.data.data.task?.schedule??'No registered schedule evidence'}. Collection uses past official sessions and observed provider candle availability; no official publication time is guaranteed. ML inference: {readable(collection.data.data.inference)}.</p></Panel>}<Panel title="Research automation" subtitle="Accepted-model P19 pipeline · separate from qualified private EOD collection">
    <QueryState query={status}>{item && <>
      <div className="inline-actions"><Badge tone="warning">{readable(item.pipeline_status)}</Badge><Badge tone="warning">Daily activation blocked</Badge><span className="caption">Scheduling disabled</span></div>
      <dl className="detail-grid"><dt>Latest attempted session</dt><dd>{item.latest_attempted_session ?? 'No daily attempt recorded'}</dd><dt>Latest successful daily session</dt><dd>{item.latest_successful_research_session ?? 'Unavailable'}</dd><dt>Source receipt for accepted daily data</dt><dd>{item.last_source_receipt ?? 'Unavailable'}</dd><dt>Feature / inference readiness</dt><dd>{readable(item.feature_readiness)} / {readable(item.inference_readiness)}</dd><dt>Historical replays</dt><dd>{item.historical_replay_count} · not new market observations</dd></dl>
      <p className="caption">These restrictions apply to retained research ingestion and model inference. Explicit transient Upstox market-data snapshots have their own observed connection and timestamp evidence.</p>
      <ul>{item.provider.reasons.map((reason) => <li key={reason}>{readable(reason)}</li>)}</ul>
      <EvidenceNote evidence={status.data} />
    </>}</QueryState>
    {timeline && <QueryState query={runs}><div className="table-scroll"><table><caption className="caption">Immutable run receipts · replay and daily attempts remain distinct</caption><thead><tr><th>Session</th><th>Mode</th><th>State</th><th>Evidence blockers</th></tr></thead><tbody>{runs.data?.data.map((run) => <tr key={run.run_id}><td>{run.session}</td><td>{readable(run.mode)}</td><td><Badge tone="warning">{readable(run.state)}</Badge></td><td>{run.reasons.map(readable).join(' · ')}</td></tr>)}</tbody></table></div>{runs.data?.data.length === 0 && <p>No published run receipt is available. A missing receipt is not a successful session.</p>}</QueryState>}
  </Panel><ProspectiveResearch /></>
}
