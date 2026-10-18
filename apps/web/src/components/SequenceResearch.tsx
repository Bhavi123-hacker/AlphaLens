import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { jsonObject } from '../api/contracts'
import { readable } from '../lib/format'
import { Badge, Empty, Panel, QueryState, Stat } from './ui'
import { Chart } from './Chart'
import { object, percent, text } from './researchFormat'

function number(value: unknown) { return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(5) : 'Unavailable' }
function central(value: unknown) {
  const scenarios = object(value).scenarios
  return object(Array.isArray(scenarios) ? scenarios.find(row => object(row).round_trip_cost_bps === 50 && object(row).slippage_bps_each_side === 5) : undefined)
}
function interval(value: unknown) {
  return Array.isArray(value) && value.length === 2 ? value.map(v => percent(v, true)).join(' to ') + ' percentage points' : 'Not available'
}

export function SequenceResearch({ v2Evaluation }: { v2Evaluation?: unknown }) {
  const query = useQuery({ queryKey: ['sequence-research'], retry: false, refetchOnWindowFocus: false, queryFn: ({ signal }) => get('/nse-market/sequence', jsonObject, signal) })
  const data = query.data?.data
  const comparisons = object(data?.comparisons)
  const entries = Object.entries(comparisons)
  const periods = object(data?.periods)
  const development = object(periods.development_report)
  const strategies = object(object(data?.economic_sensitivity).strategies)
  const curve = central(strategies.top5).curve
  const rows = Array.isArray(curve) ? curve.map(object) : []
  const v2 = object(v2Evaluation)
  const selected = object(object(v2.candidate_summary)[String(v2.selected_algorithm)])
  return <Panel title="Registered LSTM and traditional-model comparison" subtitle="Saved experiments only · comparable sequence models together; original V2 separately" className="model-research">
    <QueryState query={query} label="Reading saved model comparisons">
      {data && <><Badge tone="warning">{text(data.edge_status, 'NO_DEMONSTRATED_EDGE')}</Badge>
        <p>No new model is independently accepted. Numerical predictions are an engineering achievement; profitability and independent validation are separate evidence requirements.</p>
        {!entries.length ? <Empty title="No completed sequence comparison">No substitute metrics or simulated model results are generated.</Empty> : <>
          <div className="stat-grid"><Stat label="Historical development pairs" value={String(development.samples ?? 'Not observed')} /><Stat label="Securities in that evaluation" value={String(development.securities ?? 'Not observed')} /><Stat label="Evaluation period" value={`${text(development.first)} – ${text(development.last)}`} /><Stat label="Current compatible LSTM scores" value={String(data.current_scored_count ?? 'Not observed')} /></div>
          <p>Same eligible samples, next-open-to-fifth-close price-component target and shared dates. Training-only scaling, target purging and embargo. These previously inspected historical periods are development evidence, not genuine prospective results.</p>
          <div className="table-scroll" role="region" aria-label="Comparable model metrics" tabIndex={0}><table aria-label="Sequence experiment genuine baseline comparisons"><thead><tr><th>Model / baseline</th><th>Balanced accuracy (0–1)</th><th>ROC-AUC</th><th>Brier score ↓</th><th>Date rank IC</th><th>95% accuracy difference vs mean reversion</th></tr></thead><tbody>
            {entries.map(([name, result]) => { const row = object(result), metrics = object(row.metrics); return <tr key={name}><td><strong>{readable(name)}</strong><span className="cell-secondary">{String(metrics.sample_count ?? 'Unreported')} pairs · {String(metrics.security_count ?? 'Unreported')} securities</span></td>{['balanced_accuracy', 'roc_auc', 'brier_score', 'mean_date_rank_ic'].map(key => <td key={key}>{number(metrics[key])}</td>)}<td>{interval(object(row.uncertainty_vs_reversal).balanced_accuracy_difference_95_interval)}</td></tr> })}
          </tbody></table></div>
          <p>Intervals use whole-date moving blocks, accounting for shared market dates. Intervals containing zero do not establish outperformance. Multiple-model selection remains exploratory. Scores are uncalibrated; Ridge estimates returns and has no probability-calibration claim.</p>
          <h3>Same Top 5 reference policy, same costs</h3>
          <p>50 bps round trip + 5 bps slippage each side = 60 bps per reference round trip. All entries below are saved hypothetical reference results, not broker fills or dividend-inclusive returns.</p>
          <div className="table-scroll" role="region" aria-label="Comparable strategy economics" tabIndex={0}><table aria-label="Model Top 5 economics at registered costs"><thead><tr><th>Selection model / baseline</th><th>Gross</th><th>Net after costs</th><th>Endpoint drawdown</th><th>Membership turnover</th><th>Decisions</th></tr></thead><tbody>
            {entries.map(([name, result]) => { const reference = object(object(result).top5_reference), scenario = central(reference); return <tr key={name}><td>{readable(name)}</td>{['gross_compounded_reference_return', 'net_compounded_reference_return', 'maximum_endpoint_drawdown'].map(key => <td key={key} className={typeof scenario[key] === 'number' && scenario[key] < 0 ? 'negative-text' : ''}>{percent(scenario[key], true)}</td>)}<td>{percent(reference.mean_membership_turnover, true)}</td><td>{String(reference.decision_count ?? 'Unavailable')}</td></tr> })}
          </tbody></table></div>
          <p>Membership turnover is not traded turnover: this reference policy liquidates and re-enters every five sessions even when names repeat. Endpoint drawdown omits intervening losses. Equal-cohort references are not an independent NSE index benchmark.</p>
        </>}
        {rows.length > 0 && <Chart label="LSTM Top 5 gross and cost-sensitive hypothetical reference equity" option={{ tooltip: { trigger: 'axis' }, legend: { data: ['Gross reference', 'Net reference'] }, xAxis: { type: 'category', data: rows.map(row => row.session) }, yAxis: { type: 'value', name: 'Reference equity = 1 initially' }, series: [{ name: 'Gross reference', type: 'line', showSymbol: false, data: rows.map(row => row.gross_equity) }, { name: 'Net reference', type: 'line', showSymbol: false, data: rows.map(row => row.net_equity) }] }} />}
        {Object.keys(v2).length > 0 && <section className="research-contract"><h3>Original V2 · a separate evaluation</h3><p>Same five-session target definition, different eligible cohort, features, fitted model and expanding folds. Do not subtract its metrics from the sequence experiment to claim improvement.</p><div className="stat-grid"><Stat label="Selected V2 model" value={readable(String(v2.selected_algorithm))} /><Stat label="V2 balanced accuracy" value={percent(selected.balanced_accuracy, true)} /><Stat label="V2 evaluation pairs" value={String(selected.sample_count ?? 'Unavailable')} /><Stat label="V2 mean-reversion baseline" value={percent(object(object(v2.baseline_summary).mean_reversion).balanced_accuracy, true)} /></div><p>{text(selected.start)} – {text(selected.end)} · {String(selected.security_count ?? 'Unavailable')} securities · {text(v2.evidence_conclusion)}.</p></section>}
        <details><summary>Training windows, model architecture and original evidence</summary><p>Architecture: {text(data.architecture)}. Feature contract: {text(data.feature_version)}. No new fits or parameter search are performed by this page.</p><pre>{JSON.stringify({ periods, comparisons, model: data.model_sha256, protocol: data.protocol_sha256 }, null, 2)}</pre></details>
      </>}
    </QueryState>
  </Panel>
}
