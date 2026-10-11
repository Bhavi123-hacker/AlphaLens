import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Activity } from 'lucide-react'
import { z } from 'zod'
import { get } from '../api/client'
import { Badge, Panel, QueryState } from './ui'
import { readable } from '../lib/format'

const component = z.object({ status: z.string(), reason: z.string() }).passthrough()
const statusSchema = z.object({ observed_at: z.string(), status: z.string(), production_ready: z.literal(false),
  components: z.record(z.string(), component), probe_duration_ms: z.number() })
const metricsSchema = z.object({ scope: z.literal('CURRENT_API_PROCESS'), errors: z.number(), denied: z.number(),
  requests: z.record(z.string(), z.object({ count: z.number(), retained_samples: z.number(), p50_ms: z.number(), p95_ms: z.number() })) })
export function Operations() {
  const client = useQueryClient()
  const status = useQuery({ queryKey: ['operations', 'status'], queryFn: ({ signal }) => get('/operations/status', statusSchema, signal), staleTime: 60_000, retry: false })
  const metrics = useQuery({ queryKey: ['operations', 'metrics'], queryFn: ({ signal }) => get('/operations/metrics', metricsSchema, signal), staleTime: 60_000, retry: false })
  return <><Panel title="Local system monitoring" subtitle="Actual component checks; production clearance is separate" actions={<button className="button small" onClick={() => void client.invalidateQueries({ queryKey: ['operations'] })}><RefreshCw size={14} />Refresh system status</button>}>
    <QueryState query={status}>{status.data && <><div className="inline-actions"><Activity size={20} /><Badge tone={status.data.data.status === 'HEALTHY' ? 'positive' : 'warning'}>{status.data.data.status}</Badge><span className="caption">Observed {new Date(status.data.data.observed_at).toLocaleString()} · {status.data.data.probe_duration_ms.toFixed(1)} ms</span></div><div className="component-grid">{Object.entries(status.data.data.components).map(([name, value]) => <div className="component-card" key={name}><strong>{readable(name)}</strong><Badge tone={value.status === 'HEALTHY' ? 'positive' : 'warning'}>{readable(value.status)}</Badge><p>{readable(value.reason)}</p>{typeof value.free_bytes === 'number' && <p>{(value.free_bytes / 1024 ** 3).toFixed(1)} GiB free</p>}{typeof value.latest_state === 'string' && <p>Latest run: {readable(value.latest_state)}</p>}</div>)}</div></>}</QueryState>
    <p className="caption">Recorded probes and operational alerts are processed by explicit local commands. No page load starts a worker, downloads data or sends external notifications. Recovery: check storage and database configuration, inspect saved checkpoints, then use the documented finite recovery commands.</p></Panel>
    <Panel title="Measured API activity" subtitle="Current process only; no invented historical uptime"><QueryState query={metrics}>{metrics.data && <><p>{metrics.data.data.errors} server errors · {metrics.data.data.denied} denied or limited requests</p><div className="table-scroll" tabIndex={0} role="region" aria-label="Measured API latency table"><table><thead><tr><th>Component</th><th>Requests</th><th>Retained samples</th><th>p50 latency</th><th>p95 latency</th></tr></thead><tbody>{Object.entries(metrics.data.data.requests).map(([name, row]) => <tr key={name}><td>{readable(name)}</td><td>{row.count}</td><td>{row.retained_samples}</td><td>{row.p50_ms.toFixed(1)} ms</td><td>{row.p95_ms.toFixed(1)} ms</td></tr>)}</tbody></table></div></>}</QueryState></Panel></>
}
