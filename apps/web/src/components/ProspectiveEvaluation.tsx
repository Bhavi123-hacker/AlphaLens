import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { jsonObject } from '../api/contracts'
import { object, percent } from './researchFormat'
import { readable } from '../lib/format'
import { Badge, Panel, QueryState, Stat } from './ui'

export function ProspectiveEvaluation() {
  const [open, setOpen] = useState(false)
  const [cutoff, setCutoff] = useState('')
  const [selected, setSelected] = useState('')
  const query = useQuery({ queryKey: ['prospective-evaluation', selected], enabled: open,
    retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => get('/nse-market/prospective-evaluation' + (selected ? '?as_of=' + encodeURIComponent(selected) : ''), jsonObject, signal) })
  const data = query.data?.data
  const metrics = object(data?.metrics)
  return <Panel title="Forward forecast evaluation" subtitle="Frozen decisions and genuinely matured outcomes; historical backtests are excluded">
    <details onToggle={event => setOpen(event.currentTarget.open)}><summary>Inspect point-in-time prospective evidence</summary>
      <p>Accuracy is unavailable until qualified five-session outcomes are recorded. Duplicate original/expanded decisions count once. Scores are uncalibrated; no profitable or independently accepted strategy is established.</p>
      <form onSubmit={event => { event.preventDefault(); setSelected(cutoff) }}><label>Evaluation cutoff (ISO timestamp with timezone)<input aria-label="Evaluation cutoff" placeholder="Leave blank for now" value={cutoff} onChange={event => setCutoff(event.target.value)} /></label><button className="button small" type="submit">View saved evidence at cutoff</button></form>
      {open && <QueryState query={query}>{data && <>
        <Badge tone="warning">{Number(data.matured_outcomes) === 0 ? 'PROSPECTIVE_EVALUATION_PENDING' : 'EXPERIMENTAL — INDEPENDENT REVIEW REQUIRED'}</Badge>
        <p>Evidence cutoff: {String(data.as_of)}. Reading this view never reconciles outcomes, publishes forecasts or requests provider data.</p>
        <div className="stat-grid"><Stat label="Frozen V2 forecast records" value={String(data.raw_forecast_records ?? 'Unavailable')} /><Stat label="Unique forecast decisions" value={String(data.unique_decisions ?? 'Unavailable')} /><Stat label="Qualified matured decisions" value={String(data.matured_outcomes ?? 'Unavailable')} /><Stat label="Not yet evaluated" value={String(data.not_evaluated_decisions ?? 'Unavailable')} /></div>
        <div className="table-scroll"><table aria-label="Prospective model and baseline evaluation"><thead><tr><th>Frozen predictor</th><th>Matured samples</th><th>Accuracy</th><th>Balanced accuracy</th><th>Brier score</th></tr></thead><tbody>{Object.entries(metrics).map(([name, value]) => { const row = object(value); return <tr key={name}><td>{name === 'score' ? 'Pinned V2 model' : readable(name)}</td><td>{String(row.samples ?? 'Unavailable')}</td><td>{percent(row.accuracy, true)}</td><td>{percent(row.balanced_accuracy, true)}</td><td>{typeof row.brier_score === 'number' ? row.brier_score.toFixed(4) : 'Unavailable'}</td></tr> })}</tbody></table></div>
        <p>Threshold fixed at 0.5. Balanced accuracy requires both outcome classes. Shared dates and overlapping holding periods are dependent observations; sample count alone is not independent validation. Incompatible models/targets are separated in the exact evidence below.</p>
        <dl className="detail-grid">{Object.entries(object(data.status_counts)).map(([name, value]) => <div key={name}><dt>{readable(name)}</dt><dd>{String(value)}</dd></div>)}</dl>
        <details><summary>Forecast status, model groups and missing evidence</summary><pre>{JSON.stringify({ statuses: data.rows, total: data.rows_total, model_groups: data.model_groups, future_records_ignored: data.future_forecast_records_ignored, overlapping_records: data.overlapping_records, uncertainty: data.uncertainty }, null, 2)}</pre></details>
      </>}</QueryState>}
    </details>
  </Panel>
}
