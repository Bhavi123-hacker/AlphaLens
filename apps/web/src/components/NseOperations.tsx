import { Badge, Panel, Stat } from './ui'
import { readable } from '../lib/format'
import { useEffect, useState } from 'react'

function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : {}
}
function count(values: Record<string, unknown>, name: string) {
  const value = values[name]
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString() : 'Not observed'
}
export function NseOperations({ operations, prospective, coverage }: {
  operations?: Record<string, unknown>, prospective?: Record<string, unknown>,
  coverage?: Record<string, unknown>,
}) {
  const [now,setNow]=useState(()=>Date.now())
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),60_000);return()=>clearInterval(timer)},[])
  const saved = operations ?? {}
  const forward = prospective ?? {}
  const budget = object(saved.budget)
  const scheduler=object(saved.scheduler)
  const enabled=scheduler.state==='REGISTERED_ENABLED_LAST_VERIFIED'
  const windows=object(saved.windows_task), reservations=object(saved.reservations), collection=object(saved.collection)
  const usage=object(saved.shared_provider_usage), terminal=object(saved.last_completed)
  const sessionCoverage=object(coverage?.latest_session_coverage)
  const unfinished=Array.isArray(saved.unfinished_attempts)?saved.unfinished_attempts.map(object):[]
  const at=(value:unknown)=>{if(typeof value!=='string'||!Number.isFinite(Date.parse(value)))return 'Not observed';return new Intl.DateTimeFormat('en-IN',{dateStyle:'medium',timeStyle:'medium',timeZone:'Asia/Kolkata'}).format(new Date(value))+' IST · '+value}
  const next=typeof windows.next_run_at==='string'&&Date.parse(windows.next_run_at)>now?at(windows.next_run_at):'No future trigger in the saved observation'
  const cadence = Array.isArray(budget.cadence_ist) ? budget.cadence_ist.filter(value => typeof value === 'string').join(', ') : 'Not configured'
  return <Panel title="Daily updates and prospective validation" subtitle="Saved evidence only; viewing this panel makes no provider requests">
    <Badge tone="warning">{enabled?"Approved bounded task enabled at last verification":"Expanded recurring collection awaits explicit approval"}</Badge>
    <div className="research-status-strip" aria-label="Saved daily task status"><Badge tone={windows.state==='Running'?'accent':'neutral'}>{typeof windows.state==='string'?readable(windows.state):'Windows status not observed'}</Badge><Badge tone="warning">{saved.state==='FAILED'?'Collection failed':saved.state==='INTERRUPTED'?'Collection interrupted':saved.source_publication_complete===true?'Inspect qualified session receipts':'Fresh-session capture PENDING'}</Badge></div>
    <dl className="detail-grid"><dt>Windows task last checked</dt><dd>{at(windows.observed_at)}</dd><dt>Actual last task run</dt><dd>{at(windows.last_run_at)}</dd><dt>Windows result code</dt><dd>{count(windows,'last_result')}{windows.last_result===267014||windows.last_result===3221225786?' · Interrupted; not a successful capture':windows.last_result===0?' · Process exit only; verify source records':''}</dd><dt>Next recorded Windows run</dt><dd>{next}</dd><dt>Latest qualified retained session</dt><dd>{String(coverage?.end??'Not observed')}</dd><dt>Last terminal workflow state</dt><dd>{typeof terminal.state==='string'?readable(terminal.state):'Not observed'}</dd><dt>Last terminal workflow started</dt><dd>{at(terminal.started_at)}</dd><dt>Last terminal receipt completed</dt><dd>{at(terminal.completed_at)}</dd><dt>Shared provider ledger read at</dt><dd>{at(usage.as_of)}</dd><dt>Latest recorded provider attempt</dt><dd>{at(usage.last_attempt_at)}</dd></dl>
    {windows.enabled===false&&<p role="status">The saved Windows observation says this task is disabled. Historical registration is not current activation.</p>}
    <p>{enabled?`Last Windows registration verification: ${String(scheduler.verified_at)}. Registration is separate from successful data capture.`:"The expanded task is not enabled."} The original RELIANCE task remains separate. Configured slots: {cadence} IST, with at least {count(budget, 'cooldown_minutes')} minutes between collecting attempts. A missed trigger may run at the next operator login within the same limits.</p>
    <div className="stat-grid">
      <Stat label="Configured research securities" value={count(budget, 'expected_securities')} />
      <Stat label="Maximum stocks per run" value={count(budget, 'max_stocks_per_run')} />
      <Stat label="Maximum provider GET attempts per run" value={count(budget, 'max_requests_per_run')} />
      <Stat label="Maximum provider GET attempts per IST day" value={count(budget, 'max_requests_per_day')} />
      <Stat label="Shared provider GET attempts today" value={count(usage,'recorded_get_attempts')} note={`IST day ${String(usage.ist_day??'not observed')}; includes all clients and retries, not reserved workflow capacity`}/>
      <Stat label="Completed shared provider attempts" value={count(usage,'completed_get_attempts')} />
      <Stat label="Unresolved provider attempts" value={count(usage,'unresolved_attempts')} note="Unresolved ledger rows do not prove a completed HTTP call"/>
      <Stat label="GET attempts in last terminal run" value={count(terminal, 'source_requests_last_run')} note={`Receipt completed ${String(terminal.completed_at??'not observed')}; not today's shared usage`}/>
      <Stat label="Reserved GET attempts today" value={count(reservations,'reserved_get_attempts')} note={`IST day ${String(reservations.quota_day??'not observed')}; reservations are not actual GETs`}/>
      <Stat label="Stocks with latest retained session" value={sessionCoverage.basis==='FULL_CONFIGURED_COHORT_BEFORE_PAGINATION'?`${count(sessionCoverage,'verified_securities')} / ${count(sessionCoverage,'configured_securities')}`:'Not observed'} note={`Full configured cohort; session ${String(sessionCoverage.session??'not observed')}`}/>
      <Stat label="Stocks without that session" value={count(sessionCoverage,'pending_securities')}/>
      <Stat label="New candles in last saved collecting result" value={count(collection,'new_daily_observations')}/>
      <Stat label="Reported failed or pending observations" value={Array.isArray(collection.failures)?collection.failures.length:'Not observed'}/>
    </div>
    <p>Unfinished saved attempts: {count(saved,'unfinished_attempts_total')}. A missing terminal receipt is incomplete evidence, not proof that a worker is still running. Reservations remain consumed; actual GETs for an unfinished attempt remain unknown.</p>
    {unfinished.length>0&&<details><summary>Inspect unfinished attempt evidence</summary><div className="table-scroll"><table aria-label="Unfinished collection attempts"><thead><tr><th>Run</th><th>Recorded start</th><th>State</th><th>Reserved GET capacity</th><th>Actual GETs</th></tr></thead><tbody>{unfinished.map((row,index)=><tr key={String(row.run_id??index)}><td>{String(row.run_id??'Not observed')}</td><td>{at(row.started_at)}</td><td>{readable(String(row.state??'Not observed'))}</td><td>{count(row,'reserved_get_attempts')}</td><td>Unknown</td></tr>)}</tbody></table></div></details>}
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
