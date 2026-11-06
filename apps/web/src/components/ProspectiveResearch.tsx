import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { prospectiveStatusSchema } from '../api/daily'
import { readable } from '../lib/format'
import { Badge, EvidenceNote, Panel, QueryState } from './ui'

export function ProspectiveResearch() {
  const query = useQuery({ queryKey: ['prospective-status'], staleTime: 60_000,
    queryFn: ({ signal }) => get('/daily/prospective/status', prospectiveStatusSchema, signal) })
  const data = query.data?.data
  return <Panel title="Prospective research" subtitle="Forecasts recorded before outcomes · separate from frozen evaluation">
    <QueryState query={query}>{data && <>
      <div className="inline-actions"><Badge tone="warning">Fresh inference unavailable</Badge><Badge tone="warning">Daily shortlist unavailable</Badge></div>
      <dl className="detail-grid"><dt>Recorded forecasts</dt><dd>{data.forecasts}</dd><dt>Resolved horizons</dt><dd>{data.resolved}</dd><dt>Pending future evidence</dt><dd>{data.pending}</dd><dt>Unresolved evidence</dt><dd>{data.unresolved}</dd><dt>Local forecast store</dt><dd>{data.configured ? 'Initialized' : 'Not initialized'}</dd></dl>
      <p className="caption">Top 5, 10 and 20 research lists require permitted new data, compatible features and independent model acceptance. Historical OOS predictions do not qualify as current stock recommendations.</p>
      <ul>{data.reasons.map(reason => <li key={reason}>{readable(reason)}</li>)}</ul>
      <p className="caption">No realized performance or profitability is inferred from missing outcomes. Source checks and scheduling require explicit operator commands; opening this page does not acquire market data.</p>
      <EvidenceNote evidence={query.data} />
    </>}</QueryState>
  </Panel>
}
