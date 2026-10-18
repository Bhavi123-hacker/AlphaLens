import { ResearchSizing } from './ResearchSizing'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { get, queryString } from '../api/client'
import { jsonObject } from '../api/contracts'
import { Badge, Panel, QueryState, Stat } from './ui'
import { Chart } from './Chart'

const schema = z.object({state:z.string(),key:z.string(),v2:jsonObject.nullable(),lstm:jsonObject.nullable(),historical_comparisons:z.array(z.object({decision_session:z.string(),target_session:z.string(),actual_price_component_return:z.number(),actual_positive:z.number(),ridge_return_estimate:z.number(),scores:z.record(z.string(),z.number())})).max(100),target:z.string(),prospective_outcomes:z.literal(0),accepted_rankings:z.literal(0),provider_requests:z.literal(0),missing_evidence:z.array(z.string())})
function score(value:Record<string,unknown>|null|undefined) {return typeof value?.score==='number' ? value.score.toFixed(6) : 'No compatible saved inputs'}
export function StockResearch({instrumentKey}:{instrumentKey:string}) {
  const [open,setOpen]=useState(false)
  const query=useQuery({queryKey:['stock-research',instrumentKey],enabled:open,retry:false,queryFn:({signal})=>get('/nse-market/stock-research?'+queryString({key:instrumentKey,limit:50}),schema,signal)})
  const data=query.data?.data
  const rows=data?.historical_comparisons??[]
  return <Panel title="Stock-specific model and outcome evidence"><details onToggle={event=>setOpen(event.currentTarget.open)}><summary>Inspect experimental predictions, baselines and observed historical outcomes</summary><Badge tone="warning">EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED</Badge><p>Market prices above are separate from these dated model inputs. Scores are uncalibrated and never imply target prices or guaranteed returns.</p>{open&&<QueryState query={query}>{data&&<><div className="stat-grid"><Stat label="Preserved V2 score" value={score(data.v2)}/><Stat label="Sequence LSTM score" value={score(data.lstm)}/><Stat label="Genuine matured prospective outcomes" value={data.prospective_outcomes}/><Stat label="Accepted current rankings" value={data.accepted_rankings}/></div><p>Target: next observed session open to fifth observed close, price component only. Original raw source and inference timestamps remain available below. Missing inputs yield no model score.</p>{rows.length>0&&<><Chart label="Known-period model versus observed outcomes; no prospective performance" option={{tooltip:{trigger:'axis'},legend:{data:['Observed holding return %','Ridge return estimate %','LSTM uncalibrated score']},xAxis:{type:'category',data:rows.map(row=>row.decision_session)},yAxis:[{type:'value',name:'Price-component return %'},{type:'value',name:'Classifier score',min:0,max:1}],series:[{type:'line',name:'Observed holding return %',data:rows.map(row=>row.actual_price_component_return*100),showSymbol:false},{type:'line',name:'Ridge return estimate %',data:rows.map(row=>row.ridge_return_estimate*100),showSymbol:false},{type:'line',name:'LSTM uncalibrated score',yAxisIndex:1,data:rows.map(row=>row.scores.LSTM),showSymbol:false}]}}/><p>Known-period development observations after the training/validation windows; these years were previously inspected in V1/V2. Classifier scores and return estimates have distinct axes and meanings.</p></>}<details><summary>Original model, source and timing evidence</summary><pre>{JSON.stringify({v2:data.v2,lstm:data.lstm,missing_evidence:data.missing_evidence},null,2)}</pre></details><ResearchSizing instrumentKey={instrumentKey}/><Link to="/nse-market">Full model-versus-baseline and cost-sensitive research evidence</Link></>}</QueryState>}</details></Panel>
}
