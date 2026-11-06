import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { jsonObject } from '../api/contracts'
import { Chart } from './Chart'
import { Badge, Panel, QueryState } from './ui'
import { object, percent } from './researchFormat'

export function EconomicResearch() {
  const [open, setOpen] = useState(false)
  const query = useQuery({queryKey:['economic-research'], enabled:open, retry:false,
    refetchOnWindowFocus:false, queryFn:({signal})=>get('/nse-market/economic-research',jsonObject,signal)})
  const data = query.data?.data
  const audit = object(data?.original_five_date_attribution)
  const policies = Array.isArray(data?.policies) ? data.policies.map(object) : []
  const lstm = object(audit.LSTM)
  const curve = Array.isArray(lstm.curve) ? lstm.curve.map(object) : []
  return <Panel title="Why gross returns became negative after costs" subtitle="Original result reproduced; four predeclared development policies, no new model fits">
    <p>The original reference strategy liquidates and re-enters every five sessions. It charges the full assumed round trip even for unchanged names. Membership turnover does not reduce those costs.</p>
    <details onToggle={event=>setOpen(event.currentTarget.open)}><summary>Inspect economic attribution and the bounded lower-frequency experiment</summary>
      {open && <QueryState query={query}>{data && <>
        <Badge tone="warning">{String(data.edge_status ?? data.state)}</Badge>
        <p>All four sparse-entry policies remain negative at the central cost scenario. They hold for five sessions, then assume zero-return cash gaps; they are not ten/twenty-session predictions. Lower exposure can reduce losses without improving stock selection.</p>
        {Object.keys(audit).length>0 && <div className="table-scroll"><table aria-label="Original strategy economic attribution"><thead><tr><th>Selection</th><th>Gross</th><th>After 50 bps costs</th><th>After additional slippage</th><th>Endpoint drawdown</th><th>Losing references</th></tr></thead><tbody>{Object.entries(audit).map(([name, value])=>{const row=object(value);return <tr key={name}><td>{name}</td><td>{percent(row.gross_compounded_reference_return,true)}</td><td>{percent(row.cost_only_compounded_reference_return,true)}</td><td>{percent(row.net_compounded_reference_return,true)}</td><td>{percent(row.maximum_endpoint_drawdown,true)}</td><td>{String(row.losing_net_references)} / {String(row.decision_count)}</td></tr>})}</tbody></table></div>}
        {curve.length>0 && <Chart label="Original LSTM gross, costs and slippage reference wealth" option={{tooltip:{trigger:'axis'},legend:{data:['Gross','After costs','After slippage']},xAxis:{type:'category',data:curve.map(row=>row.session)},yAxis:{type:'value',name:'Reference wealth'},series:[['Gross','gross_equity'],['After costs','cost_only_equity'],['After slippage','net_equity']].map(([name,key])=>({name,type:'line',showSymbol:false,data:curve.map(row=>row[key])}))}}/>}
        <div className="table-scroll"><table aria-label="Registered sparse entry policies"><thead><tr><th>Saved model</th><th>Entry spacing</th><th>Approx. active fraction</th><th>Gross</th><th>Net at 60 bps</th><th>Matched baseline evidence</th></tr></thead><tbody>{policies.map(row=>{const scenarios=Array.isArray(row.scenarios)?row.scenarios.map(object):[];const central=object(scenarios[1]);return <tr key={String(row.model)+String(row.decision_spacing)}><td>{String(row.model)}</td><td>{String(row.decision_spacing)} observed decision dates</td><td>{percent(row.approximate_active_session_fraction,true)}</td><td>{percent(central.gross_compounded_reference_return,true)}</td><td>{percent(central.net_compounded_reference_return,true)}</td><td>Both paired 95% intervals include zero; exploratory known-period evidence</td></tr>})}</tbody></table></div>
        <p>Costs: 50 bps round trip plus 5 bps slippage each side. Sensitivities preserve 25/50/100 bps costs. Endpoint drawdown omits intervening daily losses. Equal cohort and mean reversion use matched dates; no qualified independent NSE index benchmark is available.</p>
        <p>Models weakened in 2026. Neither classification accuracy nor a favorable gross return proves net profitability. These inspected historical periods cannot establish independent prospective acceptance.</p>
        <details><summary>Exact sample counts, paired intervals and source hashes</summary><pre>{JSON.stringify({period:data.period,count:data.historical_prediction_count,policies,inputs:data.inputs,protocol:data.protocol_sha256,limitations:data.limitations},null,2)}</pre></details>
      </>}</QueryState>}
    </details>
  </Panel>
}
