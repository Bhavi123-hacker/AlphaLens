import { useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { z } from 'zod'
import { get, queryString } from '../api/client'
import { Panel } from './ui'
import { useProviderMemoryExpiry } from '../lib/transient'
import { readable } from '../lib/format'

const schema=z.object({symbol:z.string(),source:z.string(),observations:z.array(z.object({kind:z.string(),state:z.string(),data:z.unknown(),received_at:z.string()})),expires_in_seconds:z.number(),api_calls_this_request:z.number(),historical_pit_eligible:z.literal(false),limitations:z.array(z.string())})
const actionSchema=z.array(z.object({name:z.string(),expiry_date:z.string().nullish(),amount:z.number().nullish(),ratio:z.string().nullish(),event_details:z.array(z.object({name:z.string(),value:z.string()})).optional()}))
function ReferenceFacts({kind,data}:{kind:string;data:unknown}) {
  if(kind==='actions') {const parsed=actionSchema.safeParse(data);if(parsed.success)return <><h3>Provider corporate-action timeline</h3><p>Provider dates and event descriptions, without a completeness or historical publication-clock guarantee. No quantities, cash or model features are adjusted.</p>{parsed.data.length?<div className="table-scroll" role="region" tabIndex={0} aria-label="Provider corporate action dates"><table><thead><tr><th>Event</th><th>Provider ex/effective date</th><th>Declared amount / ratio</th><th>Dated details</th></tr></thead><tbody>{parsed.data.map((e,i)=><tr key={i}><td>{e.name}</td><td>{e.expiry_date??'Unavailable'}</td><td>{e.amount==null?'Not supplied':e.amount.toLocaleString('en-IN',{maximumFractionDigits:4})} · {e.ratio??'No ratio supplied'}</td><td>{e.event_details?.map((d,j)=><p key={j}>{d.name}: {d.value}</p>)}</td></tr>)}</tbody></table></div>:<p>No events returned; this does not establish complete coverage.</p>}</>}
  if(kind==='profile'&&data&&typeof data==='object'&&!Array.isArray(data)){const value=data as Record<string,unknown>;return <><h3>Current company reference</h3><p>Provider sector: {typeof value.sector==='string'?value.sector:'Unavailable'} · current only, not historical classification.</p><p>{typeof value.company_profile==='string'?value.company_profile:'Business description unavailable.'}</p><p>Any sector market capitalisation below describes the sector, not this company's market cap.</p><pre>{JSON.stringify(data,null,2)}</pre></>}
  return <pre>{JSON.stringify(data,null,2)}</pre>
}
export function CompanyEvidence({instrumentKey}:{instrumentKey:string}) {
  const query=useMutation({mutationFn:()=>get('/providers/upstox-private/reference?'+queryString({instrument_key:instrumentKey}),schema),gcTime:0})
  const reset=query.reset;useProviderMemoryExpiry(query.data,useCallback(()=>reset(),[reset]))
  return <Panel title="Company & Corporate Action Evidence" subtitle="Explicit current-provider reference · no historical PIT or automatic accounting adjustment"><button className="button" disabled={query.isPending} onClick={()=>query.mutate()}>Load company and corporate action reference</button>{query.error&&<p role="alert">{query.error.message}</p>}{query.data&&<><p>{query.data.data.symbol} · {query.data.data.source} · {query.data.data.api_calls_this_request} bounded provider calls. No retained payload, historical eligibility or complete action coverage is established.</p>{query.data.data.observations.map(r=><details key={r.kind}><summary>{readable(r.kind)} · {readable(r.state)} · observed {r.received_at}</summary>{r.data==null?<p>No supported response. Access or data may be unavailable.</p>:<ReferenceFacts kind={r.kind} data={r.data}/>}</details>)}<p className="caption">{query.data.data.limitations.map(readable).join(' · ')}</p></>}</Panel>
}
