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
  const operational = object(data?.operational_readiness)
  const coverage = object(operational.coverage), forecasts = object(operational.forecasts)
  const runtime = object(operational.collector_runtime), acceptance = object(operational.model_acceptance)
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
      {typeof operational.observed_at === 'string' && <section aria-label="Unified operational readiness">
        <h3>Operational acceptance</h3>
        <p>Observed {operational.observed_at}. {operational.snapshot_stale === true ? 'Operational evidence is stale; refresh the saved-source report.' : 'Saved-source report; no live provider request.'} {operational.qualification_stale === true ? 'Runtime and security qualification needs rechecking.' : ''}</p>
        <div className="stat-grid">
          <Stat label="Session-eligible universe" value={number(coverage.historical_session_eligible_securities)} note="Current listing eligibility does not establish historical tradability" />
          <Stat label="Saved forecast records / unique decisions" value={`${number(forecasts.raw_forecast_records)} / ${number(forecasts.unique_decisions)}`} />
          <Stat label="Qualified forward outcomes" value={number(forecasts.matured_outcomes)} note={text(forecasts.measurement_status)} />
          <Stat label="Independently accepted models" value={number(acceptance.accepted_models)} note="Experimental scores do not establish an investment edge" />
          <Stat label="Active collector dependency advisories" value={number(runtime.active_dependency_advisories)} note={`Cutover: ${text(runtime.cutover_status)}`} />
          <Stat label="Candidate collector dependency advisories" value={number(runtime.candidate_dependency_advisories)} />
        </div>
        <details><summary>Runtime, scheduler, security and publication evidence</summary><pre>{JSON.stringify({ runtime, security: operational.security, scheduler: operational.scheduler, publication: operational.last_successful_data_publication, quota: operational.provider_quota, missing: coverage.missing_security_details }, null, 2)}</pre></details>
      </section>}
      <p>{number(alerts.total)} recorded local alerts. This is saved alert history; older conditions may have cleared. No email, broker action or outbound notification is sent.</p>
      {rows.length > 0 && <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable local collection alerts"><table aria-label="Local collection alerts"><thead><tr><th>Recorded alert</th><th>Observed at</th><th>Status</th></tr></thead><tbody>{rows.map((row, index) => <tr key={text(row.id) + index}><td>{readable(text(row.title ?? row.code ?? row.event_key))}<span className="cell-secondary">{Array.isArray(object(row.evidence).reasons) ? (object(row.evidence).reasons as unknown[]).map(value => readable(text(value))).join('; ') : ''}</span></td><td>{text(row.created_at ?? row.event_at)}</td><td>{readable(text(row.lifecycle ?? row.state ?? row.status))}</td></tr>)}</tbody></table></div>}
    </>}</QueryState>
  </Panel>
}
