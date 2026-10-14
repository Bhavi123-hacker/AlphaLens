import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { get, queryString } from '../api/client'
import { currency, localTime } from '../lib/format'
import { terminalSchema, type ProviderInstrument, type ProviderSnapshot } from '../api/terminal'
import { ProviderSearch } from './ProviderWorkspace'
import { Badge, Panel, QueryState } from './ui'
import { Chart } from './Chart'
import { lineChart } from '../lib/visual-options'
import { toggleFavorite, usePreferences } from '../lib/preferences'

function observedChange(item: ProviderSnapshot) {
  const raw = item.quote.state === 'VALIDATED_SNAPSHOT' ? item.quote.change_percent : item.change_percent
  return raw == null ? null : Number(raw)
}
export function UpstoxWatchlist({ comparison = false }: { comparison?: boolean }) {
  const preferences = usePreferences()
  const [chosen, setChosen] = useState<ProviderInstrument[]>([]); const [loaded, setLoaded] = useState(false)
  const [minimumVolume, setMinimumVolume] = useState(''); const [minPrice, setMinPrice] = useState(''); const [minRSI, setMinRSI] = useState('')
  const queryKey = ['provider-cohort', ...chosen.map(i => i.provider_key)]; const client = useQueryClient()
  const query = useQuery({ queryKey, enabled: loaded && chosen.length > 0, retry: false, staleTime: 600_000, gcTime: 0, refetchOnWindowFocus: false, refetchOnReconnect: false,
    queryFn: ({ signal }) => get(`/providers/upstox-private/snapshot?${queryString({ instrument_keys: chosen.map(i => i.provider_key).join(',') })}`, terminalSchema, signal) })
  const data = query.data?.data
  useEffect(() => { if (!data?.items.length) return; const remaining = Math.min(...data.items.map(i => i.cache_ttl_seconds - i.cache_age_seconds)); const timer = setTimeout(() => { setLoaded(false); client.removeQueries({ queryKey, exact: true }) }, Math.max(0, remaining) * 1000); return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, client])
  const rows = (data?.items ?? []).filter(i => {
    const value = i.quote.state === 'VALIDATED_SNAPSHOT' ? i.quote.ltp : i.latest_close
    return (!minimumVolume || (i.rows.at(-1)?.volume ?? -Infinity) >= Number(minimumVolume)) && (!minPrice || value != null && Number(value) >= Number(minPrice)) && (!minRSI || (i.indicators.rsi_14?.points.at(-1)?.value ?? -Infinity) >= Number(minRSI))
  })
  const ranked = rows.filter(i => observedChange(i) !== null).slice().sort((a, b) => observedChange(b)! - observedChange(a)!)
  const dates = useMemo(() => [...new Set((data?.items ?? []).flatMap(i => i.rows.slice(-120).map(r => r.session)))].sort(), [data])
  return <Panel className="current-cohort" title={comparison ? 'Upstox selected-stock comparison' : 'Upstox selected watchlist'} subtitle="Up to three current-master NSE equities per explicit request. No full-market breadth or model ranking.">
    <ProviderSearch onSelect={i => { setLoaded(false); setChosen(v => v.some(x => x.provider_key === i.provider_key) ? v : [...v, i].slice(-3)); if (!preferences.favorites.some(f => f.security_id === 'upstox:' + i.provider_key)) toggleFavorite({ security_id: 'upstox:' + i.provider_key, symbol: i.symbol, name: i.name || '' }) }} />
    <div className="cohort-controls"><div className="favorite-strip">{chosen.map(i => <button className="chip selected" key={i.provider_key} onClick={() => { setLoaded(false); setChosen(v => v.filter(x => x.provider_key !== i.provider_key)) }}>{i.symbol} ×</button>)}</div><button className="button primary" disabled={!chosen.length || query.isFetching} onClick={() => loaded ? void query.refetch() : setLoaded(true)}>{loaded ? 'Refresh selected watchlist' : 'Load selected watchlist'}</button></div>
    {!chosen.length && <p className="caption">Find and add exact current-master identities. No default prices or inferred NSE instruments.</p>}
    {loaded && <QueryState query={query} label="Reading bounded selected-cohort snapshots">{data && <><div className="inline-actions"><Badge tone="accent">{data.queried_count} queried identities · selected watchlist</Badge><Badge>Transient snapshots · not streaming</Badge></div><div className="filters"><label>Minimum candle volume<input type="number" aria-label="Private watchlist minimum volume" min="0" value={minimumVolume} onChange={e => setMinimumVolume(e.target.value)} /></label><label>Minimum observed price<input type="number" min="0" value={minPrice} onChange={e => setMinPrice(e.target.value)} /></label><label>Minimum RSI 14<input type="number" min="0" max="100" value={minRSI} onChange={e => setMinRSI(e.target.value)} /></label></div><p className="caption">{rows.length} private watchlist matches · filters exclude missing inputs. Quote and candle changes have separate bases; dates are shown for every row.</p>
      <div className="provider-heatmap" role="region" aria-label="Selected provider watchlist heatmap">{rows.map(i => { const change = observedChange(i); return <Link key={i.instrument_key} className={change == null ? '' : change < 0 ? 'tile-negative' : change > 0 ? 'tile-positive' : ''} to={`/stocks/${encodeURIComponent('upstox:' + i.instrument_key)}`}><strong>{i.symbol}</strong><span>{change === null ? 'Change unavailable' : `${change > 0 ? '+' : ''}${change.toFixed(2)}%`}</span><small>{i.quote.state === 'VALIDATED_SNAPSHOT' ? 'LTP vs provider previous close' : `Candle change · ${i.latest_session}`}</small></Link> })}</div>
      <div className="table-scroll" role="region" aria-label="Selected provider watchlist screener"><table><thead><tr><th>NSE equity</th><th>Observed price</th><th>Price type / timestamp</th><th>EOD date</th><th>Candle volume</th><th>RSI 14</th></tr></thead><tbody>{rows.map(i => <tr key={i.instrument_key}><td><Link to={`/stocks/${encodeURIComponent('upstox:' + i.instrument_key)}`}>{i.symbol}</Link><span className="cell-secondary">{i.identity.isin}</span></td><td className="numeric">₹{currency(i.quote.state === 'VALIDATED_SNAPSHOT' ? i.quote.ltp : i.latest_close)}</td><td>{i.quote.state === 'VALIDATED_SNAPSHOT' ? 'LTP snapshot' : 'Provider daily close'}<span className="cell-secondary">{i.quote.state === 'VALIDATED_SNAPSHOT' ? localTime(i.quote.last_trade_at) : i.latest_session}</span></td><td>{i.latest_session || 'Unavailable'}</td><td>{i.rows.at(-1)?.volume.toLocaleString('en-IN') ?? 'Unavailable'}</td><td>{i.indicators.rsi_14?.points.at(-1)?.value?.toFixed(2) ?? 'Unavailable'}</td></tr>)}</tbody></table></div>
      <div className="two-columns">{[['Selected gainers', ranked.filter(i => observedChange(i)! > 0)], ['Selected losers', ranked.filter(i => observedChange(i)! < 0).reverse()]].map(([title, items]) => <div className="selected-movers" key={String(title)}><h3>{String(title)}</h3>{(items as ProviderSnapshot[]).length ? (items as ProviderSnapshot[]).map(i => <Link key={i.instrument_key} to={`/stocks/${encodeURIComponent('upstox:' + i.instrument_key)}`}><span>{i.symbol}</span><strong className={observedChange(i)! < 0 ? 'negative-text' : 'positive-text'}>{observedChange(i)!.toFixed(2)}%</strong></Link>) : <p>No observed matches in this selected cohort.</p>}</div>)}</div>
      {comparison && dates.length > 0 && <><Chart height={430} label="Selected Upstox daily close comparison" option={lineChart(dates, data.items.map(i => { const map = new Map(i.rows.slice(-120).map(r => [r.session, Number(r.close)])); return { name: i.symbol, values: dates.map(d => map.get(d) ?? null) } }), 2)} /><p className="caption">Last 120 returned daily observations; nominal provider INR closes, unknown adjustment bases, gaps retained. No total-return or predictive comparison.</p></>}
    </>}</QueryState>}
  </Panel>
}
