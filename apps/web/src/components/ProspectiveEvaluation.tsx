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
  const topN = object(data?.top_n)
  const declarations = Array.isArray(topN.results) ? topN.results.map(object) : []
  const comparisons = object(data?.baseline_comparisons)
  return <Panel title="Forward forecast evaluation" subtitle="Frozen decisions and genuinely matured outcomes; historical backtests are excluded">
    <details onToggle={event => setOpen(event.currentTarget.open)}><summary>Inspect point-in-time prospective evidence</summary>
      <p>Accuracy is unavailable until qualified five-session outcomes are recorded. Duplicate original/expanded decisions count once. Scores are uncalibrated; no profitable or independently accepted strategy is established.</p>
      <form onSubmit={event => { event.preventDefault(); setSelected(cutoff) }}><label>Evaluation cutoff (ISO timestamp with timezone)<input aria-label="Evaluation cutoff" placeholder="Leave blank for now" value={cutoff} onChange={event => setCutoff(event.target.value)} /></label><button className="button small" type="submit">View saved evidence at cutoff</button></form>
      {open && <QueryState query={query}>{data && <>
        <Badge tone="warning">{Number(data.matured_outcomes) === 0 ? 'PROSPECTIVE_EVALUATION_PENDING' : 'EXPERIMENTAL — INDEPENDENT REVIEW REQUIRED'}</Badge>
        <p>Evidence cutoff: {String(data.as_of)}. Reading this view never reconciles outcomes, publishes forecasts or requests provider data.</p>
        <div className="stat-grid"><Stat label="Frozen V2 forecast records" value={String(data.raw_forecast_records ?? 'Unavailable')} /><Stat label="Unique forecast decisions" value={String(data.unique_decisions ?? 'Unavailable')} /><Stat label="Qualified matured decisions" value={String(data.matured_outcomes ?? 'Unavailable')} /><Stat label="Not yet evaluated" value={String(data.not_evaluated_decisions ?? 'Unavailable')} /></div>
        {Number(data.matured_outcomes) === 0 && <p role="status">Insufficient forward evaluation data.</p>}
        <div className="table-scroll"><table aria-label="Prospective model and baseline evaluation"><thead><tr><th>Frozen predictor</th><th>Matured samples</th><th>Accuracy</th><th>Balanced accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>Brier score</th></tr></thead><tbody>{Object.entries(metrics).map(([name, value]) => { const row = object(value); return <tr key={name}><td>{name === 'score' ? 'Pinned V2 model' : readable(name)}</td><td>{String(row.samples ?? 'Unavailable')}</td>{['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1'].map(metric => <td key={metric}>{percent(row[metric], true)}</td>)}<td>{typeof row.roc_auc === 'number' ? row.roc_auc.toFixed(4) : 'Unavailable'}</td><td>{typeof row.brier_score === 'number' ? row.brier_score.toFixed(4) : 'Unavailable'}</td></tr> })}</tbody></table></div>
        <p>Threshold fixed at 0.5. Balanced accuracy requires both outcome classes. Shared dates and overlapping holding periods are dependent observations; sample count alone is not independent validation. Incompatible models/targets are separated in the exact evidence below.</p>
        <p>Undefined metrics remain unavailable. ROC-AUC requires both classes. Brier and score bins describe uncalibrated scores; they do not establish a calibrated probability of gain. Dependence-aware confidence intervals require the registered future decision-date sample.</p>
        {Object.keys(comparisons).length > 0 && <div className="table-scroll"><table aria-label="Matched prospective baseline comparisons"><thead><tr><th>Frozen baseline</th><th>Matched outcomes</th><th>Missing pairs</th><th>Model accuracy</th><th>Baseline accuracy</th><th>Balanced accuracy difference</th></tr></thead><tbody>{Object.entries(comparisons).map(([name, value]) => { const row = object(value), candidate = object(row.candidate), baseline = object(row.baseline), delta = object(row.candidate_minus_baseline); return <tr key={name}><td>{readable(name)}</td><td>{String(row.matched_samples ?? 'Unavailable')}</td><td>{String(row.excluded_missing_pairs ?? 'Unavailable')}</td><td>{percent(candidate.accuracy, true)}</td><td>{percent(baseline.accuracy, true)}</td><td>{percent(delta.balanced_accuracy, true)}</td></tr> })}</tbody></table></div>}
        <h3>Frozen Top 5 / 10 / 20 outcome coverage</h3>
        <p>Each row uses an original declared selection. Hit rates stay unavailable until the entire declared cohort matures, including members outside Top 5. Overlapping declarations are not pooled; equal-cohort comparisons are not an NSE index benchmark.</p>
        <div className="stat-grid"><Stat label="Original ranking declarations" value={String(topN.declarations ?? 'Unavailable')} /><Stat label="Complete matured declarations" value={String(topN.complete_declarations ?? 'Unavailable')} /></div>
        {declarations.length > 0 ? <div className="table-scroll"><table aria-label="Frozen Top-N forward hit rates"><thead><tr><th>Original declaration / observation</th><th>Qualified cohort outcomes</th><th>Top 5</th><th>Top 10</th><th>Top 20</th><th>Equal cohort</th></tr></thead><tbody>{declarations.map((row, index) => { const selections = object(object(row.selections).score); return <tr key={String(row.declaration_id ?? index)}><td>{String(row.declaration_id ?? 'Unavailable').slice(0, 12)}<span className="cell-secondary">{String(row.observation_session ?? 'Unavailable')} · {row.complete === true ? 'Complete reference cohort' : 'Awaiting full cohort'}</span></td><td>{String(row.qualified_outcomes ?? 'Unavailable')} / {String(row.declared_securities ?? 'Unavailable')}</td>{['5', '10', '20'].map(count => { const selected = object(selections[count]); return <td key={count}>{percent(selected.hit_rate, true)}<span className="cell-secondary">{String(selected.qualified_selected_outcomes ?? 'Unavailable')} / {String(selected.selected_securities ?? 'Unavailable')} selected outcomes</span></td> })}<td>{percent(row.equal_cohort_hit_rate, true)}</td></tr> })}</tbody></table></div> : <p>No qualified original ranking declaration is available at this cutoff.</p>}
        <dl className="detail-grid">{Object.entries(object(data.status_counts)).map(([name, value]) => <div key={name}><dt>{readable(name)}</dt><dd>{String(value)}</dd></div>)}</dl>
        <details><summary>Forecast status, model groups and missing evidence</summary><pre>{JSON.stringify({ statuses: data.rows, total: data.rows_total, model_groups: data.model_groups, baseline_comparisons: comparisons, score_diagnostics: metrics, top_n: topN, future_records_ignored: data.future_forecast_records_ignored, overlapping_records: data.overlapping_records, uncertainty: data.uncertainty }, null, 2)}</pre></details>
      </>}</QueryState>}
    </details>
  </Panel>
}
