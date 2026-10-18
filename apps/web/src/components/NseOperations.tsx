import { Badge, Panel, Stat } from './ui'
import { readable } from '../lib/format'

function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : {}
}
function count(values: Record<string, unknown>, name: string) {
  const value = values[name]
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString() : 'Not observed'
}
export function NseOperations({ operations, prospective }: {
  operations?: Record<string, unknown>, prospective?: Record<string, unknown>,
}) {
  const saved = operations ?? {}
  const forward = prospective ?? {}
  const budget = object(saved.budget)
  const scheduler=object(saved.scheduler)
  const enabled=scheduler.state==='REGISTERED_ENABLED_LAST_VERIFIED'
  const cadence = Array.isArray(budget.cadence_ist) ? budget.cadence_ist.filter(value => typeof value === 'string').join(', ') : 'Not configured'
  return <Panel title="Daily updates and prospective validation" subtitle="Saved evidence only; viewing this panel makes no provider requests">
    <Badge tone="warning">{enabled?"Approved bounded task enabled at last verification":"Expanded recurring collection awaits explicit approval"}</Badge>
    <p>{enabled?`Last Windows registration verification: ${String(scheduler.verified_at)}. Registration is separate from successful data capture.`:"The expanded task is not enabled."} The original RELIANCE task remains separate. Configured slots: {cadence} IST, with at least {count(budget, 'cooldown_minutes')} minutes between collecting attempts. A missed trigger may run at the next operator login within the same limits.</p>
    <div className="stat-grid">
      <Stat label="Configured research securities" value={count(budget, 'expected_securities')} />
      <Stat label="Maximum stocks per run" value={count(budget, 'max_stocks_per_run')} />
      <Stat label="Maximum provider GET attempts per run" value={count(budget, 'max_requests_per_run')} />
      <Stat label="Maximum provider GET attempts per IST day" value={count(budget, 'max_requests_per_day')} />
      <Stat label="Provider GETs in last saved run" value={count(saved, 'source_requests_last_run')} />
    </div>
    <p data-testid="nse-operational-state">Last workflow state: {typeof saved.state === 'string' ? readable(saved.state) : 'No saved run'}.</p>
    {typeof saved.error_code === 'string' && <p role="status">{readable(saved.error_code)}. {typeof saved.message === 'string' ? saved.message : 'Check readiness before retrying.'}</p>}
    <div className="stat-grid">
      <Stat label="Frozen global cohort declarations" value={count(forward, 'declarations')} />
      <Stat label="Frozen expanded security forecasts" value={count(forward, 'unique_security_forecasts')} />
      <Stat label="Genuinely matured expanded outcomes" value={count(forward, 'matured_security_outcomes')} />
      <Stat label="Complete global outcome cohorts" value={count(forward, 'complete_global_declarations')} />
    </div>
    <p>Global selections and baseline ranks are frozen before their future entry. Performance remains pending until the declared cohort has eligible outcomes for five genuinely subsequent sessions, official session evidence and later source retrieval. Missing or excluded stocks are never dropped to improve results. Per-shard ranking statistics are not averaged into market-wide performance.</p>
    <p>Original V2 forecasts remain separate. Accepted ML rankings remain unavailable pending the registered evidence requirements and actual independent review.</p>
  </Panel>
}
