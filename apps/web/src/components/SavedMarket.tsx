import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { get, queryString } from '../api/client'
import { priceOption } from '../lib/chart-options'
import { currency, readable } from '../lib/format'
import { useDebounce } from '../lib/useDebounce'
import { Chart } from './Chart'
import { Badge, Empty, Panel, QueryState } from './ui'

const money = z.string().nullable()
const candle = z.object({ session: z.string(), open: money, high: money, low: money, close: money, volume: z.number().int().nonnegative().nullable() })
const security = z.object({ key: z.string(), symbol: z.string(), name: z.string().nullable(),
  session: z.string().nullable(), freshness: z.string(), previous_close: money, change: money,
  change_percent: money, received_at: z.string().nullable(), source: z.string(),
  open: money, high: money, low: money, close: money, volume: z.number().int().nonnegative().nullable(),
})
const metadata = z.object({ mode: z.literal('SAVED_COMPLETED_SESSION_NOT_LIVE'),
  latest_observed_session: z.string(), as_of: z.string(), price_basis: z.string(),
  provider_requests: z.literal(0), configured_securities: z.number().int(), latest_session_securities: z.number().int(),
})
const listing = metadata.extend({ total: z.number().int(), rows: z.array(security).max(50) })
const history = metadata.extend({ security, rows: z.array(candle).max(120) })
const number = (value: string | null) => value === null ? 'Unavailable' : currency(value)

export function SavedMarket() {
  const [search, setSearch] = useState(''), [order, setOrder] = useState('symbol')
  const q = useDebounce(search)
  const result = useQuery({ queryKey: ['saved-market', q, order], retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => get('/nse-market/saved-market?' + queryString({ q, order, limit: 25 }), listing, signal) })
  const data = result.data?.data
  return <Panel title="Saved NSE market movements" subtitle="Private retained daily candles; opening saved charts makes no provider requests">
    <div className="cohort-controls"><label>Search saved NSE prices<input aria-label="Search saved NSE prices" maxLength={128} value={search} onChange={event => setSearch(event.target.value)} /></label>
      <label>Market view<select aria-label="Saved market view" value={order} onChange={event => setOrder(event.target.value)}>
        <option value="symbol">All saved securities</option><option value="gainers">Top gainers</option><option value="losers">Top losers</option><option value="volume">Volume leaders</option>
      </select></label></div>
    <QueryState query={result} label="Reading verified saved candle view">{data && <>
      <Badge tone="warning">COMPLETED-SESSION DATA · NOT LIVE STREAMING</Badge>
      <p>{data.latest_session_securities} / {data.configured_securities} with latest observed session {data.latest_observed_session}. View published {data.as_of}. Price basis: {readable(data.price_basis)}.</p>
      <p>Changes compare adjacent observed cohort sessions and exclude dividends. The exchange calendar is incomplete. Missing prior observations stay unavailable. Leaders exclude stale or missing data.</p>
      {data.rows.length ? <div className="table-scroll"><table aria-label="Saved NSE market movements"><thead><tr><th>Security</th><th>Last saved close</th><th>Observed change</th><th>Volume</th><th>Session / freshness</th></tr></thead><tbody>{data.rows.map(row => <tr key={row.key}>
        <td><Link to={'/stocks/' + encodeURIComponent('upstox:' + row.key)}>{row.symbol}</Link><span className="cell-secondary">{row.name}</span></td>
        <td>{number(row.close)}</td><td>{number(row.change)}<span className="cell-secondary">{row.change_percent === null ? 'Unavailable' : Number(row.change_percent).toFixed(2) + '%'}</span></td>
        <td>{row.volume === null ? 'Unavailable' : row.volume.toLocaleString()}</td><td>{row.session ?? 'Unavailable'}<span className="cell-secondary">{readable(row.freshness)}</span></td>
      </tr>)}</tbody></table></div> : <Empty title="No eligible saved observations">No prices or leaders are substituted.</Empty>}
    </>}</QueryState>
  </Panel>
}

export function SavedStock({ instrumentKey }: { instrumentKey: string }) {
  const [line, setLine] = useState(false)
  const result = useQuery({ queryKey: ['saved-stock', instrumentKey], retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => get('/nse-market/saved-history?' + queryString({ key: instrumentKey }), history, signal) })
  const data = result.data?.data
  const option = useMemo(() => {
    const option = priceOption(data?.rows ?? [], {}, line)
    const axes = option.yAxis as { name?: string }[]
    axes[0].name = 'INR · saved provider basis'
    return option
  }, [data, line])
  return <Panel title="Saved private OHLCV chart" subtitle="Up to 120 observed cohort sessions; no provider requests">
    <QueryState query={result}>{data && <>
      <Badge tone="warning">{readable(data.security.freshness)} · NOT A LIVE QUOTE</Badge>
      <h3>{data.security.symbol} · {data.security.name}</h3>
      <p>Saved close ₹{number(data.security.close)} · {data.security.session ?? 'Unavailable'}. Change {number(data.security.change)} ({data.security.change_percent === null ? 'Unavailable' : Number(data.security.change_percent).toFixed(2) + '%'}). Volume {data.security.volume?.toLocaleString() ?? 'Unavailable'}.</p>
      <p>Retrieved {data.security.received_at ?? 'Unavailable'}. Source: {data.security.source}. Price basis: {readable(data.price_basis)}. Adjacent observed-session changes are price components; complete exchange-calendar and economic-action evidence is unavailable.</p>
      <div className="segmented" role="group" aria-label="Saved chart type"><button aria-pressed={!line} onClick={() => setLine(false)}>Candles</button><button aria-pressed={line} onClick={() => setLine(true)}>Line</button></div>
      {data.rows.some(row => row.close !== null) ? <Chart option={option} height={450} label={`Saved ${data.security.symbol} daily price and volume`} /> : <Empty title="No saved candles for this identity">Missing values remain empty.</Empty>}
    </>}</QueryState>
  </Panel>
}
