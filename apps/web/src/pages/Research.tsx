import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { ArrowUpRight, Info, FlaskConical } from 'lucide-react'
import { get, queryString, validateRange } from '../api/client'
import { comparisonSchema, modelSchema, predictionSchema, type JsonObject, type Model, type Stock } from '../api/contracts'
import { metric, readable } from '../lib/format'
import { Badge, Drawer, Empty, EvidenceNote, Heading, Panel, QueryState, Stat, StockSearch } from '../components/ui'
import { Chart } from '../components/Chart'
import { barOption } from '../lib/chart-options'

const classMetrics = ['balanced_accuracy', 'accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'pr_auc_average_precision', 'brier_score', 'log_loss', 'mean_rank_ic', 'mean_top_minus_bottom']
const regMetrics = ['mae', 'rmse', 'r2', 'spearman', 'mean_rank_ic', 'mean_top_minus_bottom', 'mean_top_quintile', 'mean_bottom_quintile']
const definitions: Record<string, string> = {
  balanced_accuracy: 'Average recall across the two classes. Around 50% suggests chance-like directional discrimination even when raw accuracy is higher.',
  accuracy: 'Fraction of correct class labels at the frozen model threshold. A dominant negative class can make this look strong without useful directional skill.',
  roc_auc: 'Probability a positive example ranks above a negative example. Around 0.5 indicates no discrimination.',
  pr_auc_average_precision: 'Precision-recall summary; interpret against the positive class rate, particularly with imbalanced labels.',
  brier_score: 'Mean squared probability error. Lower is better; compare with the same-fold naive baseline.',
  mean_rank_ic: 'Stored average session rank correlation between predictions and realized raw targets. Positive correlation is not proof of profitable trading.',
  mean_top_minus_bottom: 'Stored top-minus-bottom quintile raw-target spread. It excludes execution costs and unresolved economic actions.',
  mae: 'Mean absolute return-prediction error. Lower is better; units are return fractions.',
  rmse: 'Root mean squared return-prediction error; more sensitive to large errors.',
  r2: 'Explained variation relative to a constant mean. Negative values can indicate worse performance than that reference.',
  spearman: 'Rank association between predictions and realized targets across the stored evaluation samples.',
}
function numeric(value: unknown) { return typeof value === 'number' && Number.isFinite(value) ? value : null }
function object(value: unknown): JsonObject { return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonObject : {} }
function period(phase: string) { return phase === 'development' ? '2022–2024 development OOS' : phase === '2025' ? '2025 candidate confirmation' : '2026 final holdout · read-only' }
function metricValue(value: unknown, name: string) { return metric(value, ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1'].includes(name)) }

export function Research() {
  const [params, setParams] = useSearchParams(); const horizon = ['1', '5', '10', '20'].includes(params.get('horizon') ?? '') ? params.get('horizon')! : '5'
  const [task, setTask] = useState('classification'); const [family, setFamily] = useState('all'); const [phase, setPhase] = useState('development')
  const [measure, setMeasure] = useState('balanced_accuracy'); const [selected, setSelected] = useState<Model | null>(null)
  const models = useQuery({ queryKey: ['models'], queryFn: ({ signal }) => get('/research/models?limit=500', z.array(modelSchema), signal) })
  const evaluation = useQuery({ queryKey: ['evaluation'], queryFn: ({ signal }) => get('/research/evaluation', comparisonSchema, signal) })
  const rows = models.data?.data.filter((m) => String(m.horizon) === horizon && m.task === task && m.phase === phase && (family === 'all' || family === m.model_family)) ?? []
  const families = [...new Set(models.data?.data.filter((m) => m.task === task && String(m.horizon) === horizon).map((m) => m.model_family))].sort()
  const metrics = task === 'classification' ? classMetrics : regMetrics
  const aggregates = evaluation.data?.data.models.filter((row) => String(row.horizon) === horizon && row.task === task && (family === 'all' || row.model_family === family)) ?? []
  const chartRows = phase === 'development' ? aggregates.map((row) => ({ name: readable(String(row.model_family)), value: numeric(object(object(row.fold_metrics)[measure]).mean) }))
    : rows.map((row) => ({ name: readable(row.model_family), value: numeric(row.metrics[measure]) }))
  const bounded = ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'pr_auc_average_precision', 'brier_score'].includes(measure)
  const chart = barOption(chartRows.map((row) => row.name), chartRows.map((row) => row.value), readable(measure), bounded ? [0, 1] : ['spearman', 'mean_rank_ic'].includes(measure) ? [-1, 1] : undefined)
  const candidate = evaluation.data?.data.selected[horizon]
  return <><Heading eyebrow="Chronological machine-learning research" title="ML research lab">Inspect completed fits and genuinely out-of-sample evidence.<br />No retraining, inference or model promotion occurs here.</Heading>
    <div className="research-callout"><FlaskConical size={22} /><div><strong>Real observations. Research conclusions.</strong><p>The archive uses final-vintage assumptions. Economic evidence remains incomplete; every selected candidate retains insufficient-evidence status.</p></div><Badge tone="warning">NOT PRODUCTION VALIDATED</Badge></div>
    <div className="filters"><label>Horizon<select aria-label="Research horizon" value={horizon} onChange={(e) => setParams({ horizon: e.target.value })}>{[1, 5, 10, 20].map((h) => <option value={h} key={h}>{h} sessions</option>)}</select></label>
      <label>Task<select aria-label="Model task" value={task} onChange={(e) => { setTask(e.target.value); setMeasure(e.target.value === 'classification' ? 'balanced_accuracy' : 'mae'); setFamily('all') }}><option value="classification">Classification</option><option value="regression">Regression</option></select></label>
      <label>Model family<select aria-label="Model family" value={family} onChange={(e) => setFamily(e.target.value)}><option value="all">All returned families</option>{families.map((f) => <option key={f} value={f}>{readable(f)}</option>)}</select></label>
      <label>Evaluation period<select aria-label="Evaluation period" value={phase} onChange={(e) => setPhase(e.target.value)}><option value="development">Development OOS · 2022–2024</option><option value="2025">Confirmation · 2025</option><option value="2026">Final holdout · 2026</option></select></label></div>
    {phase === '2026' && <div className="notice warning"><Info size={18} /><p><strong>2026 final holdout — already evaluated under the frozen protocol.</strong> These are stored results, separate from development and confirmation. Viewing this page does not repeat evaluation or permit tuning.</p></div>}
    <div className="stats-grid"><Stat label="Returned matching fits" value={models.isSuccess ? rows.length : 'Unavailable'} note={period(phase)} /><Stat label="OOS samples across displayed fits" value={models.isSuccess ? rows.reduce((n, row) => n + row.scored_test_rows, 0).toLocaleString() : 'Unavailable'} note="Repeated samples across competing models; not unique observations" /><Stat label="Selected research configuration" value={candidate ? readable(String(candidate.model_family)) : 'Unavailable'} note={`${horizon}-session candidate · ${candidate ? String(candidate.task) : ''}`} /><Stat label="Candidate status" value="Insufficient evidence" tone="warning-text" note={candidate ? String(candidate.research_status) : 'Awaiting selection evidence'} /></div>
    <Panel title={phase === 'development' ? 'Model comparison · stored fold means' : 'Model comparison · stored period metrics'} subtitle={period(phase)} actions={<label className="inline-label">Metric<select aria-label="Comparison metric" value={measure} onChange={(e) => setMeasure(e.target.value)}>{metrics.map((m) => <option value={m} key={m}>{readable(m)}</option>)}</select></label>}>
      <QueryState query={phase === 'development' ? evaluation : models}>{chartRows.length ? <Chart option={chart} label={`${readable(measure)} by returned model family, ${period(phase)}`} /> : <Empty title="No returned model combination">Choose another task, horizon or family.</Empty>}</QueryState>
      <p className="metric-explainer"><Info size={16} />{definitions[measure] ?? 'Stored metric from the frozen evaluation protocol. Interpret alongside class balance, naive comparisons and sample size.'}</p><EvidenceNote evidence={evaluation.data} />
    </Panel>
    {phase === 'development' && <Panel title="Fold stability & ranking" subtitle="Stored mean, dispersion and worst-fold evidence; no new selection"><QueryState query={evaluation}><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table><thead><tr><th>Family</th><th>Mean metric</th><th>Standard deviation</th><th>Best / worst</th><th>Rank IC</th><th>Top − bottom</th><th>Folds beating naive</th><th>OOS samples</th></tr></thead><tbody>{aggregates.map((row) => { const stats = object(object(row.fold_metrics)[measure]); return <tr key={String(row.model_family)}><td>{readable(String(row.model_family))}</td><td className="numeric">{metricValue(stats.mean, measure)}</td><td className="numeric">{metric(stats.std)}</td><td className="numeric">{metricValue(stats.best, measure)} / {metricValue(stats.worst, measure)}</td><td className="numeric">{metric(row.mean_rank_ic)}</td><td className="numeric">{metric(row.mean_top_minus_bottom, true)}</td><td className="numeric">{metric(row.folds_beating_naive, true)}</td><td className="numeric">{typeof row.oos_samples === 'number' ? row.oos_samples.toLocaleString() : 'Unavailable'}</td></tr> })}</tbody></table></div></QueryState></Panel>}
    <Panel title="Individual fits & naive comparisons" subtitle="Click a persisted fit for configuration, lineage and local prediction reads"><QueryState query={models}>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table><thead><tr><th>Model / fold</th><th>{task === 'classification' ? 'Accuracy' : 'MAE'}</th><th>{task === 'classification' ? 'Balanced acc.' : 'RMSE'}</th><th>{task === 'classification' ? 'ROC-AUC' : 'R²'}</th><th>{task === 'classification' ? 'Brier' : 'Spearman'}</th><th>Naive {readable(measure)}</th><th>Rank IC</th><th>Train / OOS</th><th>Details</th></tr></thead><tbody>{rows.map((row) => <tr key={row.model_run_id}><td><strong>{readable(row.model_family)}</strong><span className="cell-secondary">{row.fold_id} · {period(row.phase)}</span></td>
        {(task === 'classification' ? ['accuracy', 'balanced_accuracy', 'roc_auc', 'brier_score'] : ['mae', 'rmse', 'r2', 'spearman']).map((m) => <td className="numeric" key={m}>{metricValue(row.metrics[m], m)}</td>)}<td className="numeric">{metricValue(row.naive[measure], measure)}</td><td className="numeric">{metric(row.metrics.mean_rank_ic)}</td><td className="numeric">{row.training_rows.toLocaleString()}<span className="cell-secondary">{row.scored_test_rows.toLocaleString()}</span></td><td><button className="icon-button" aria-label={`Inspect ${row.model_family} ${row.fold_id}`} onClick={() => setSelected(row)}><ArrowUpRight size={17} /></button></td></tr>)}</tbody></table></div>
      {!rows.length && models.isSuccess && <Empty title="No matching persisted fits" />}
      <EvidenceNote evidence={models.data} /></QueryState></Panel>
    {selected && <Drawer title={`${readable(selected.model_family)} · ${selected.horizon} sessions`} close={() => setSelected(null)}><ModelDetails model={selected} /></Drawer>}
  </>
}
function ModelDetails({ model }: { model: Model }) {
  const detail = useQuery({ queryKey: ['model-detail', model.model_run_id], queryFn: ({ signal }) => get(`/research/models/${model.model_run_id}`, modelSchema, signal) })
  return <><Badge tone={model.phase === '2026' ? 'warning' : 'accent'}>{period(model.phase)}</Badge><QueryState query={detail}>{detail.data && <><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table><thead><tr><th>Metric</th><th>Model</th><th>Naive</th></tr></thead><tbody>{Object.entries(model.metrics).filter(([, value]) => typeof value === 'number' || value === null).map(([key, value]) => <tr key={key}><td title={definitions[key]}>{readable(key)}</td><td className="numeric">{metricValue(value, key)}</td><td className="numeric">{metricValue(model.naive[key], key)}</td></tr>)}</tbody></table></div>
      <details className="technical-details"><summary>Frozen model configuration & lineage</summary><pre>{JSON.stringify(detail.data.data.model_identity, null, 2)}</pre></details><EvidenceNote evidence={detail.data} /></>}</QueryState><PredictionInspector model={model} /></>
}
function PredictionInspector({ model }: { model: Model }) {
  const [security, setSecurity] = useState<Stock | null>(null); const [start, setStart] = useState(''); const [end, setEnd] = useState(''); const [error, setError] = useState('')
  const [request, setRequest] = useState<{ security: string; start: string; end: string } | null>(null)
  const predictions = useQuery({ queryKey: ['predictions', model.model_run_id, request], enabled: !!request,
    queryFn: ({ signal }) => get(`/research/predictions?${queryString({ model_id: model.model_run_id, security_id: request!.security, start: request!.start, end: request!.end, limit: 100 })}`, z.array(predictionSchema), signal) })
  return <section className="prediction-inspector"><h3>Inspect persisted OOS predictions</h3><p className="caption">Explicit bounded read, at most 100 records. MODEL ESTIMATE · NOT GUARANTEED. These are historical FOLD_TEST outputs, not live signals. {model.task === 'classification' ? 'Score is model probability for the positive class; prediction is the frozen-threshold class label. Model probability is distinct from signal confidence.' : 'Prediction is the model-estimated raw return fraction for this horizon.'}</p><StockSearch onSelect={setSecurity} placeholder="Choose prediction security" />{security && <Badge>{security.latest_observed_symbol || security.security_id}</Badge>}
    <form className="custom-dates" onSubmit={(event) => { event.preventDefault(); if (!security) { setError('Choose an evidenced security first.'); return } try { validateRange(start, end); setRequest({ security: security.security_id, start, end }); setError('') } catch (e) { setError((e as Error).message) } }}><label>From<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label><label>To<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label><button className="button small">Read predictions</button></form>{error && <p role="alert" className="warning-text">{error}</p>}
    {request && <QueryState query={predictions}>{predictions.data && <><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table><thead><tr><th>Session</th><th>Score</th><th>Prediction</th><th>Role</th></tr></thead><tbody>{predictions.data.data.map((row) => <tr key={row.prediction_id}><td>{row.session_date}</td><td className="numeric">{metric(row.score)}</td><td className="numeric">{metric(row.prediction)}</td><td>{row.role}</td></tr>)}</tbody></table></div>{!predictions.data.data.length && <Empty title="No OOS predictions in this scope">The selected fold/security/date range has no stored predictions.</Empty>}{predictions.data.page?.has_more && <p className="warning-text">More predictions exist. Narrow the dates to inspect a smaller scope.</p>}<EvidenceNote evidence={predictions.data} /></>}</QueryState>}
  </section>
}
