import { useMemo, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, CandlestickChart, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { get, queryString } from '../api/client'
import { jsonObject } from '../api/contracts'
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
  data_status:z.string().optional(), independent_acceptance_status:z.string().optional(), availability_state:z.string().optional(), exchange:z.string().nullable().optional(), segment:z.string().nullable().optional(), support_status:z.string().optional(), support_reason:z.string().optional(), ml_status:z.string().optional(),
  latest_feature_exclusions:z.array(z.string()).optional(), identity_status:jsonObject.nullable().optional(),
  descriptive_risk:jsonObject.optional(), saved_prediction:jsonObject.nullable().optional(),
  current_identity:z.object({symbol:z.string(),name:z.string(),exchange:z.string(),source_date:z.string().nullable(),snapshot_id:z.string()}).nullable().optional(),
  current_identity_status:z.string().optional(),
})
const metadata = z.object({ mode: z.literal('SAVED_COMPLETED_SESSION_NOT_LIVE'),
  latest_observed_session: z.string().nullable(), as_of: z.string(), price_basis: z.string(),
  provider_requests: z.literal(0), configured_securities: z.number().int(), latest_session_securities: z.number().int(),
})
const listing = metadata.extend({ total: z.number().int(), rows: z.array(security).max(50) })
const history = metadata.extend({ security, rows: z.array(candle).max(120) })
const number = (value: string | null) => value === null ? 'Unavailable' : currency(value)
const movement = (value: string | null) => value !== null && Number.isFinite(Number(value))
  ? Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : '' : ''

export function SavedMarket() {
  const [search, setSearch] = useState(''), [order, setOrder] = useState('symbol')
  const [preview, setPreview] = useState<string | null>(null)
  const q = useDebounce(search)
  const result = useQuery({ queryKey: ['saved-market', q, order], retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => get('/nse-market/saved-market?' + queryString({ q, order, limit: 25 }), listing, signal) })
  const data = result.data?.data
  return <Panel className="saved-market-terminal" title="Saved NSE market movements" subtitle="Private retained daily candles; opening saved charts makes no provider requests">
    <div className="cohort-controls"><label>Search saved NSE prices<input aria-label="Search saved NSE prices" maxLength={128} value={search} onChange={event => setSearch(event.target.value)} /></label>
      <label>Market view<select aria-label="Saved market view" value={order} onChange={event => setOrder(event.target.value)}>
        <option value="symbol">All saved securities</option><option value="gainers">Top gainers</option><option value="losers">Top losers</option><option value="volume">Volume leaders</option>
      </select></label></div>
    <QueryState query={result} label="Reading verified saved candle view">{data && <>
      <Badge tone="warning">COMPLETED-SESSION DATA · NOT LIVE STREAMING</Badge>
      <div className="saved-market-status" aria-label="Saved market source status"><div><span>Latest saved session</span><strong>{data.latest_observed_session ?? 'Unavailable'}</strong></div><div><span>Saved session coverage</span><strong>{data.latest_session_securities} / {data.configured_securities}</strong></div><div><span>Data mode</span><strong>Saved daily OHLCV</strong></div><div><span>Provider requests from this view</span><strong>{data.provider_requests}</strong></div></div>
      <p className="caption">{data.latest_session_securities} / {data.configured_securities} with latest observed session {data.latest_observed_session}. View published {data.as_of}. Price basis: {readable(data.price_basis)}.</p>
      <p>Changes compare adjacent observed cohort sessions and exclude dividends. The exchange calendar is incomplete. Missing prior observations stay unavailable. Leaders exclude stale or missing data.</p>
      <div className="saved-market-workspace"><div className="saved-market-watchlist">
      {data.rows.length ? <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable saved market watchlist"><table aria-label="Saved NSE market movements"><thead><tr><th>Security</th><th>Last saved close</th><th>Observed change</th><th>Volume</th><th>Session / freshness</th></tr></thead><tbody>{data.rows.map(row => <tr key={row.key} className={preview === row.key ? 'selected-market-row' : undefined}>
        <td><Link to={'/stocks/' + encodeURIComponent('upstox:' + row.key)}>{row.symbol}</Link><span className="cell-secondary">{row.name}</span><button className="market-preview-button" aria-label={`Preview ${row.symbol} saved chart`} aria-pressed={preview === row.key} onClick={() => setPreview(row.key)}><CandlestickChart size={13} aria-hidden="true" />Preview chart</button></td>
        <td className="numeric">{row.close === null ? 'Unavailable' : '₹' + number(row.close)}</td><td className={`numeric ${movement(row.change_percent)}`}>{row.change_percent !== null && Number(row.change_percent) > 0 ? <ArrowUpRight size={14} aria-hidden="true" /> : row.change_percent !== null && Number(row.change_percent) < 0 ? <ArrowDownRight size={14} aria-hidden="true" /> : null}{number(row.change)}<span className="cell-secondary">{row.change_percent === null ? 'Unavailable' : Number(row.change_percent).toFixed(2) + '%'}</span></td>
        <td>{row.volume === null ? 'Unavailable' : row.volume.toLocaleString()}</td><td>{row.session ?? 'Unavailable'}<span className="cell-secondary">{readable(row.freshness)}</span></td>
      </tr>)}</tbody></table></div> : <Empty title="No eligible saved observations">No prices or leaders are substituted.</Empty>}</div>
      <aside className="saved-market-preview" aria-label="Saved chart workspace">{preview ? <><div className="preview-workspace-toolbar"><span>CHART WORKSPACE</span><button className="button small" onClick={() => setPreview(null)}>Close preview</button></div><SavedStock key={preview} instrumentKey={preview} compact /><Link className="button small" to={'/stocks/' + encodeURIComponent('upstox:' + preview)}>Open full stock research <ArrowUpRight size={14} aria-hidden="true" /></Link></> : <div className="market-preview-prompt"><CandlestickChart size={38} aria-hidden="true" /><h3>Your market research workspace</h3><p>Preview a security beside the watchlist to inspect its genuine saved daily candles and volume.</p><span><Search size={14} aria-hidden="true" />Search saved prices or choose gainers, losers and volume leaders.</span><small>No live quote is requested. Missing observations remain unavailable.</small></div>}</aside></div>
    </>}</QueryState>
  </Panel>
}

export function SavedStock({ instrumentKey, compact = false }: { instrumentKey: string; compact?: boolean }) {
  const [line, setLine] = useState(false)
  const [showIdentity, setShowIdentity] = useState(false)
  const identity = useQuery({queryKey:['saved-identity-history',instrumentKey],enabled:showIdentity,retry:false,
    queryFn:({signal})=>get('/nse-market/identity-history?'+queryString({key:instrumentKey}),jsonObject,signal)})
  const result = useQuery({ queryKey: ['saved-stock', instrumentKey], retry: false, refetchOnWindowFocus: false,
    queryFn: ({ signal }) => get('/nse-market/saved-history?' + queryString({ key: instrumentKey }), history, signal) })
  const data = result.data?.data
  const option = useMemo(() => {
    const option = priceOption(data?.rows ?? [], {}, line)
    const axes = option.yAxis as { name?: string }[]
    axes[0].name = compact ? 'INR' : 'INR · saved provider basis'
    return option
  }, [data, line, compact])
  return <Panel className={compact ? 'compact-saved-stock' : 'saved-stock-detail'} title="Saved private OHLCV chart" subtitle="Up to 120 observed cohort sessions; no provider requests">
    <QueryState query={result}>{data && <>
      <Badge tone="warning">{readable(data.security.freshness)} · NOT A LIVE QUOTE</Badge>
      {data.security.current_identity && <p className="caption breakable">Current master listing: {data.security.current_identity.symbol} · {data.security.current_identity.name} · {data.security.current_identity.exchange}. Master observed {data.security.current_identity.source_date ?? 'date unavailable'}. Saved candles retain their original observed aliases below.</p>}
      <div className="saved-stock-headline"><div><h3>{data.security.symbol} · {data.security.name}</h3><span>{data.security.session ?? 'No saved session'} · Saved close</span></div><div className="saved-stock-price"><strong>{data.security.close === null ? 'Unavailable' : '₹' + number(data.security.close)}</strong><span className={movement(data.security.change_percent)}>{number(data.security.change)} ({data.security.change_percent === null ? 'Unavailable' : Number(data.security.change_percent).toFixed(2) + '%'})</span></div></div>
      {compact && <div className="saved-ohlc-strip">{(['open', 'high', 'low', 'volume'] as const).map(field => <div key={field}><span>{readable(field)}</span><strong>{field === 'volume' ? data.security.volume?.toLocaleString() ?? 'Unavailable' : number(data.security[field])}</strong></div>)}</div>}
      {!compact && <>
      <p className="breakable">Exact saved identity: {data.security.key}. Symbols and company names are observed aliases; different ISINs are never joined automatically.</p>
      {data.security.availability_state && <p role="status">{readable(data.security.availability_state)}</p>}
      {data.security.support_status && <p>{readable(data.security.support_status)}. {readable(data.security.support_reason ?? '')}</p>}
      {data.security.identity_status?.state === 'STALE' && <p>Dated verified identity only; current listing and provider access are unverified.</p>}
      {data.security.data_status && <p>{data.security.data_status} ? {data.security.independent_acceptance_status}</p>}
      {data.security.ml_status && <p>ML evidence: {readable(data.security.ml_status)}. {data.security.latest_feature_exclusions?.map(readable).join('; ')}</p>}
      {data.security.saved_prediction && <p className="breakable">Saved experimental five-session score: {String(data.security.saved_prediction.score)}. {String(data.security.saved_prediction.score_status ?? 'SAVED_HISTORICAL_SCORE')}. Observation {String(data.security.saved_prediction.session)}; originally generated {String(data.security.saved_prediction.inference_at)}. Model {String(data.security.saved_prediction.model_id)}. {data.security.saved_prediction.matches_latest_retained_session ? 'Matches the latest retained session.' : 'Dated score from an earlier session; this request did not generate a new forecast.'} Calibrated probability unavailable.</p>}
      {data.security.descriptive_risk && <dl className="detail-grid"><dt>Observed daily price volatility</dt><dd>{typeof data.security.descriptive_risk.daily_return_sd_20 === 'number' ? `${(data.security.descriptive_risk.daily_return_sd_20 * 100).toFixed(2)}%` : 'Unavailable'}</dd><dt>Observed 60-session price drawdown</dt><dd>{typeof data.security.descriptive_risk.observed_price_drawdown_60 === 'number' ? `${(data.security.descriptive_risk.observed_price_drawdown_60 * 100).toFixed(2)}%` : 'Unavailable'}</dd><dt>Risk evidence</dt><dd>{String(data.security.descriptive_risk.observation_session ?? 'No eligible observation')}; {readable(String(data.security.descriptive_risk.reason ?? data.security.descriptive_risk.basis))}. Price components exclude dividends; no complete exchange calendar or annualized risk is implied.</dd></dl>}
      <p>Saved close ₹{number(data.security.close)} · {data.security.session ?? 'Unavailable'}. Change {number(data.security.change)} ({data.security.change_percent === null ? 'Unavailable' : Number(data.security.change_percent).toFixed(2) + '%'}). Volume {data.security.volume?.toLocaleString() ?? 'Unavailable'}.</p>
      <p>Retrieved {data.security.received_at ?? 'Unavailable'}. Source: {data.security.source}. Price basis: {readable(data.price_basis)}. Adjacent observed-session changes are price components; complete exchange-calendar and economic-action evidence is unavailable.</p>
      </>}
      <div className="segmented" role="group" aria-label="Saved chart type"><button aria-pressed={!line} onClick={() => setLine(false)}>Candles</button><button aria-pressed={line} onClick={() => setLine(true)}>Line</button></div>
      {data.rows.some(row => row.close !== null) ? <Chart option={option} height={compact ? 420 : 450} label={`Saved ${data.security.symbol} daily price and volume`} /> : <Empty title="No saved candles for this identity">Missing values remain empty.</Empty>}
      {compact ? <p className="caption">{readable(data.security.freshness)}. Source: {data.security.source}. Received {data.security.received_at ?? 'Unavailable'}. Price basis: {readable(data.price_basis)}. Adjacent observed-session price changes exclude dividends; the exchange calendar and corporate-action evidence remain incomplete.</p> : <details onToggle={event=>setShowIdentity(event.currentTarget.open)}><summary>Observed master identity changes</summary><p>Snapshots record observed symbols, names and presence. Absence is not verified delisting. No historical listing interval is inferred.</p>{showIdentity && <QueryState query={identity}>{identity.data && <pre>{JSON.stringify(identity.data.data,null,2)}</pre>}</QueryState>}</details>}
    </>}</QueryState>
  </Panel>
}
