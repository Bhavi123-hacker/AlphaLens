import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { privateSchema } from '../api/upstox-private'
import { get } from '../api/client'
import { priceOption } from '../lib/chart-options'
import { decimalHeadline, rangeStart } from '../lib/format'
import { Chart } from './Chart'
import { Badge, Panel, QueryState, Stat } from './ui'


export function UpstoxPrivateView() {
  const [enabled, setEnabled] = useState(false)
  const [range, setRange] = useState('1Y')
  const query = useQuery({ queryKey: ['private-upstox-reliance'], enabled, retry: false, staleTime: 600_000,
    refetchOnWindowFocus: false, refetchOnReconnect: false,
    queryFn: ({ signal }) => get('/providers/upstox-private/reliance', privateSchema, signal) })
  const data = query.data?.data
  const rows = useMemo(() => {
    if (!data?.rows.length) return []
    const start = rangeStart(data.rows.at(-1)!.session, range, data.rows[0].session)
    return data.rows.filter(r => r.session >= start)
  }, [data, range])
  const option = useMemo(() => {
    const opt = priceOption(rows, data?.indicators ?? {}, false)
    return { ...opt, yAxis: Array.isArray(opt.yAxis) ? opt.yAxis.map((axis, i) => i === 0 ? { ...axis, name: 'INR · provider basis unknown' } : axis) : opt.yAxis }
  }, [data, rows])
  return <Panel title="Private Upstox NSE view" subtitle="Provider candles are separate from the frozen research archive. No retained ingestion or ML prediction follows.">
    {!enabled && <><p>Load a bounded RELIANCE candle request and current-session timing check through the protected backend. Results stay in process memory for ten minutes. No token reaches this browser.</p><button className="button" onClick={() => setEnabled(true)}>Load private RELIANCE candles</button></>}
    {enabled && <QueryState query={query}>{data && <>
      <Badge tone="warning">{data.state}</Badge>{data.current_session_status && <p className="caption">{data.current_session_status.replaceAll("_", " ")}. A provider daily candle is distinct from an independently verified official final close.</p>}
      {data.state === 'AVAILABLE_PRIVATE_TRANSIENT' && <>
        <div className="stats-grid"><Stat label="Latest provider daily close" value={data.latest_close ? `₹${decimalHeadline(data.latest_close)}` : 'Unavailable'} note={`${data.latest_session} · NSE · Upstox V3`} /><Stat label="Observed candle change" value={data.change_percent ? `${Number(data.change_percent).toFixed(2)}%` : 'Unavailable'} note="Previous returned candle; corporate actions unverified" /><Stat label="Price basis" value="UNKNOWN" note="No archive merge or adjustment assumption" /></div>
        <div className="segmented" role="group" aria-label="Private provider date range">{['1M','3M','6M','1Y','3Y','5Y','ALL'].map(r => <button key={r} aria-pressed={range === r} onClick={() => setRange(r)}>{r}</button>)}</div>
        <Chart option={option} height={660} label={`Private Upstox RELIANCE NSE daily candles ending ${data.latest_session}; volume and descriptive indicators`} />
        <p className="caption">{rows.length} returned candle dates. Missing exchange sessions are not independently established. Indicators use provider-observed slots; warm-up gaps remain empty. All means the bounded returned window.</p>
        <p className="warning-text">Official final-close status, publication clocks, adjustment basis and corporate actions are unverified. Current-session quotes are separate and unavailable here. Charts do not establish model eligibility.</p>
        <details><summary>Provider Evidence Passport</summary><dl className="detail-grid"><dt>Instrument</dt><dd>{data.instrument_key}</dd><dt>Retrieved</dt><dd>{data.received_at}</dd><dt>Source</dt><dd>{data.source}</dd><dt>Retention</dt><dd>Transient memory only</dd><dt>Current inference</dt><dd>Unavailable</dd></dl><p>{data.passport?.blockers.join(' · ')}</p></details>
        {data.feature_readiness && <details><summary>Current model feature readiness</summary><p>{data.feature_readiness.descriptive_available_count} of {data.feature_readiness.required_count} numerical inputs can be described from returned slots; {data.feature_readiness.model_eligible_count} model-eligible inputs. No accepted current models, prospective forecasts or Top 5/10/20 rankings.</p><div className="table-scroll"><table><thead><tr><th>Stored model column order</th><th>Descriptive availability</th><th>Eligibility exclusion</th></tr></thead><tbody>{data.feature_readiness.features.map(f => <tr key={f.column}><td>{f.column}</td><td>{f.descriptive_value_available ? 'Available, descriptive only' : 'Unavailable'}</td><td>{f.exclusion}</td></tr>)}</tbody></table></div></details>}
      </>}
    </>}</QueryState>}
  </Panel>
}
