import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { decimalHeadline } from '../lib/format'
import { privateSchema } from '../api/upstox-private'
import { Badge, Panel, QueryState } from './ui'

export function UpstoxWatchlist() {
  const [enabled, setEnabled] = useState(false)
  const [minimumVolume, setMinimumVolume] = useState('')
  const query = useQuery({ queryKey: ['private-upstox-reliance'], enabled, retry: false,
    staleTime: 600_000, refetchOnWindowFocus: false, refetchOnReconnect: false,
    queryFn: ({ signal }) => get('/providers/upstox-private/reliance', privateSchema, signal) })
  const data = query.data?.data
  const latest = data?.rows.at(-1)
  const matched = latest && (!minimumVolume || latest.volume >= Number(minimumVolume))
  const value = data?.change_percent ? Number(data.change_percent) : null
  return <Panel title="Private current provider watchlist" subtitle="One verified identity; no full-NSE breadth or historical common-equity eligibility claim.">
    {!enabled && <button className="button" onClick={() => setEnabled(true)}>Load private watchlist metrics</button>}
    {enabled && <QueryState query={query}>{data && data.state !== 'AVAILABLE_PRIVATE_TRANSIENT' && <Badge tone="warning">{data.state}</Badge>}{data?.state === 'AVAILABLE_PRIVATE_TRANSIENT' && <>
      <p>Provider session {data.latest_session} · NSE · Upstox V3 · price basis UNKNOWN · memory only</p>
      <Badge tone="warning">1 queried / 1 verified watchlist identity; full eligible NSE denominator unavailable</Badge>
      <label>Private watchlist minimum volume<input type="number" min="0" value={minimumVolume} onChange={e => setMinimumVolume(e.target.value)} /></label>
      <p>{matched ? 1 : 0} private watchlist matches</p>
      {matched && <div role="region" aria-label="Private provider watchlist heatmap and screener">
        <Link className={value !== null && value < 0 ? 'negative' : 'positive'} to="/stocks/tejhq%3Aisin%3AINE002A01018">RELIANCE · {value === null ? 'Change unavailable' : `${value.toFixed(2)}%`}</Link>
        <table><thead><tr><th>Security</th><th>Provider date</th><th>Daily close</th><th>Volume</th><th>RSI 14</th><th>ATR 14</th></tr></thead><tbody><tr><td>RELIANCE · INE002A01018</td><td>{latest.session}</td><td>₹{decimalHeadline(latest.close)}</td><td>{latest.volume}</td><td>{data.indicators.rsi_14?.points.at(-1)?.value?.toFixed(2) ?? 'Unavailable'}</td><td>{data.indicators.atr_14?.points.at(-1)?.value?.toFixed(2) ?? 'Unavailable'}</td></tr></tbody></table>
      </div>}
      <p className="caption">Change compares returned candles. Corporate actions and missing sessions are unverified; these descriptive metrics cannot rank model opportunities.</p>
    </>}</QueryState>}
  </Panel>
}
