import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { jsonObject } from '../api/contracts'
import { readable } from '../lib/format'
import { Panel, QueryState, Stat } from './ui'

const object = (value: unknown): Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
const text = (value: unknown) => typeof value === 'string' ? value : 'Not observed'
const number = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString() : 'Not observed'

export function CollectionHealth() {
  const query = useQuery({ queryKey: ['nse-collection-health'], retry: false, refetchOnWindowFocus: false,
    refetchInterval: 60_000, queryFn: ({ signal }) => get('/nse-market/collection-health', jsonObject, signal) })
  const data = query.data?.data
  const quota = object(data?.quota), freshness = object(data?.forecast_freshness)
  const alerts = object(data?.local_alerts)
  const rows = Array.isArray(alerts.alerts) ? alerts.alerts.map(object) : []
  const snapshot = typeof data?.read_at === 'string'
  return <Panel title="Collection monitoring and local alerts" subtitle="Saved operational evidence; refreshes locally each minute without provider calls">
    <QueryState query={query}>{data && <>
      {snapshot ? <>
        <p>Snapshot {text(data.read_at)}. {data.snapshot_stale === true ? 'This monitoring snapshot is stale.' : 'Inspect its date before acting.'} Expected completed NSE session: {text(data.expected_trading_session)}; coverage session: {text(data.coverage_session)}.</p>
        <div className="stat-grid">
          <Stat label="Accepted / configured securities" value={`${number(data.accepted_securities)} / ${number(data.configured_securities)}`} />
          <Stat label="Missing securities" value={number(data.missing_securities)} />
          <Stat label="Reserved request capacity remaining" value={number(quota.reserved_requests_remaining)} note="Unused capacity does not authorize another collecting slot" />
          <Stat label="Remaining approved run slots" value={number(quota.run_slots_remaining)} />
          <Stat label="Saved predictions for expected session" value={freshness.fresh_for_expected_session === true ? 'Verified fresh for saved expected session' : 'Unverified or stale'} note={`Observation ${text(freshness.observation_session)}`} />
        </div>
        <details><summary>Per-security missing reasons and latest run evidence</summary><pre>{JSON.stringify({ missing: data.missing_security_details, reasons: data.missing_data_reasons, last_successful: data.last_successful_run, last_failed: data.last_failed_run, latest_terminal: data.latest_terminal, quota: data.quota }, null, 2)}</pre></details>
      </> : <p>No collection-monitoring snapshot has been published. A successful task exit or an empty alert list is not proof of complete data.</p>}
      <p>{number(alerts.total)} recorded local alerts. This is saved alert history; older conditions may have cleared. No email, broker action or outbound notification is sent.</p>
      {rows.length > 0 && <div className="table-scroll"><table aria-label="Local collection alerts"><thead><tr><th>Recorded alert</th><th>Observed at</th><th>Status</th></tr></thead><tbody>{rows.map((row, index) => <tr key={text(row.id) + index}><td>{readable(text(row.title ?? row.code ?? row.event_key))}<span className="cell-secondary">{Array.isArray(object(row.evidence).reasons) ? (object(row.evidence).reasons as unknown[]).map(value => readable(text(value))).join('; ') : ''}</span></td><td>{text(row.created_at ?? row.event_at)}</td><td>{readable(text(row.lifecycle ?? row.state ?? row.status))}</td></tr>)}</tbody></table></div>}
    </>}</QueryState>
  </Panel>
}
