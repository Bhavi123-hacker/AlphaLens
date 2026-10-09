import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueries, useQuery } from '@tanstack/react-query'
import { Star, ArrowUpRight } from 'lucide-react'
import { collect, get, queryString, validateRange } from '../api/client'
import { detailSchema, featureControls, indicatorSchema, priceSchema, type Indicator } from '../api/contracts'
import { decimalHeadline, exact, rangeStart } from '../lib/format'
import { toggleFavorite, usePreferences } from '../lib/preferences'
import { Chart } from './Chart'
import { priceOption } from '../lib/chart-options'
import { Badge, EvidenceNote, Panel, QueryState, Stat } from './ui'

export function StockWorkspace({ securityId, compact = false }: { securityId: string; compact?: boolean }) {
  const detail = useQuery({ queryKey: ['stock', securityId], queryFn: ({ signal }) => get(`/stocks/${encodeURIComponent(securityId)}`, detailSchema, signal) })
  return <QueryState query={detail}>{detail.data && <StockChart key={securityId} securityId={securityId} detail={detail.data} compact={compact} />}</QueryState>
}
function StockChart({ securityId, detail, compact }: { securityId: string; detail: Awaited<ReturnType<typeof get<typeof detailSchema>>>; compact: boolean }) {
  const stock = detail.data; const latest = [...stock.observed_identity_evidence].sort((a, b) => a.last_observed.localeCompare(b.last_observed) || a.first_observed.localeCompare(b.first_observed) || a.symbol.localeCompare(b.symbol)).at(-1)
  const [range, setRange] = useState('1Y'); const [startInput, setStartInput] = useState(''); const [endInput, setEndInput] = useState('')
  const [custom, setCustom] = useState<{ start: string; end: string } | null>(null); const [dateError, setDateError] = useState('')
  const [line, setLine] = useState(false); const [features, setFeatures] = useState<string[]>(compact ? [] : ['sma_200'])
  const preferences = usePreferences(); const favorite = preferences.favorites.some((f) => f.security_id === securityId)
  const start = custom?.start ?? rangeStart(stock.last_observed, range, stock.first_observed); const end = custom?.end ?? stock.last_observed
  const history = useQuery({ queryKey: ['history', securityId, start, end], queryFn: ({ signal }) => collect(`/stocks/${encodeURIComponent(securityId)}/history`, priceSchema, { start, end }, signal) })
  const indicators = useQueries({ queries: features.map((feature) => ({ queryKey: ['indicator', securityId, feature, start, end], queryFn: async ({ signal }: { signal: AbortSignal }) => {
    let offset = 0; const points: Indicator['points'] = []; let last
    do { last = await get(`/stocks/${encodeURIComponent(securityId)}/indicators?${queryString({ feature, start, end, limit: 500, offset })}`, indicatorSchema, signal); points.push(...last.data.points); offset += last.data.points.length
      if (last.page?.has_more && last.data.points.length === 0) throw new Error('Inconsistent indicator pagination')
    } while (last.page?.has_more && offset < 5000)
    return { ...last, data: { ...last.data, points }, truncated: !!last.page?.has_more }
  } })) })
  const evidence = useMemo(() => Object.fromEntries(indicators.flatMap((result, i) => result.data ? [[features[i], result.data.data]] : [])), [indicators, features])
  const option = useMemo(() => priceOption(history.data?.data ?? [], evidence, line), [history.data, evidence, line])
  const lastPrice = history.data?.data.filter((r) => r.close !== null).at(-1)
  const missing = history.data?.data.filter((r) => r.close === null).length ?? 0
  const osc = features.filter((key) => !key.startsWith('sma_') && !key.startsWith('ema_')).length
  function changeFeature(feature: string) {
    setFeatures((values) => values.includes(feature) ? values.filter((v) => v !== feature) : [...values, feature].slice(-4))
  }
  return <><Panel title={latest?.symbol || securityId} subtitle={latest?.name || 'Dated security identity'} actions={<div className="inline-actions">
    <Badge tone="accent">Historical · NSE</Badge><button className={`icon-button ${favorite ? 'favorited' : ''}`} aria-label={favorite ? 'Remove browser favorite' : 'Save browser favorite'} aria-pressed={favorite} onClick={() => toggleFavorite({ security_id: securityId, symbol: latest?.symbol || securityId, name: latest?.name || '' })}><Star size={18} /></button>
    {compact && <Link className="icon-button" aria-label="Open stock analysis" to={`/stocks/${encodeURIComponent(securityId)}`}><ArrowUpRight size={18} /></Link>}</div>}>
    <div className="chart-stats"><Stat label="Last observed close" value={lastPrice ? `₹${decimalHeadline(lastPrice.close)}` : 'Unavailable'} note={lastPrice ? `${lastPrice.session} · ${lastPrice.quality}` : undefined} /><Stat label="Price basis" value="Raw unadjusted" note="Price movement excludes economic adjustments" /><Stat label="Identity" value={latest?.isin || 'Provisional'} note={latest?.analytical_type ?? 'Research classification'} /></div>
    <div className="chart-toolbar"><div className="segmented" role="group" aria-label="Historical date range">{['1M', '3M', '6M', '1Y', '3Y', '5Y', 'ALL'].map((value) => <button key={value} aria-pressed={range === value && !custom} onClick={() => { setRange(value); setCustom(null); setStartInput(''); setEndInput('') }}>{value}</button>)}</div>
      <div className="segmented" role="group" aria-label="Price chart type"><button aria-pressed={!line} onClick={() => setLine(false)}>Candles</button><button aria-pressed={line} onClick={() => setLine(true)}>Line</button></div></div>
    {!compact && <><form className="custom-dates" onSubmit={(event) => { event.preventDefault(); try { const a = startInput || start, b = endInput || end; validateRange(a, b); setCustom({ start: a, end: b }); setDateError('') } catch (error) { setDateError((error as Error).message) } }}>
      <label>From<input type="date" value={startInput || start} min={stock.first_observed} max={stock.last_observed} onChange={(e) => setStartInput(e.target.value)} /></label><label>To<input type="date" value={endInput || end} min={stock.first_observed} max={stock.last_observed} onChange={(e) => setEndInput(e.target.value)} /></label><button className="button small">Apply dates</button>{dateError && <span role="alert">{dateError}</span>}</form>
      <div className="indicator-controls" role="group" aria-label="Stored technical indicators">{featureControls.map(([key, title, kind]) => <button className={`chip ${features.includes(key) ? 'selected' : ''}`} key={key} aria-pressed={features.includes(key)} title={kind === 'price' ? 'Stored price overlay' : 'Stored feature in a separate pane'} onClick={() => changeFeature(key)}>{title}</button>)}</div><p className="caption">Up to four stored series; choosing a fifth replaces the oldest selection. Oscillators have separate linked panes.</p></>}
    <QueryState query={history} label="Reading genuine OHLCV history">{history.data && <><Chart option={option} height={compact ? 355 : 460 + osc * 100} label={`Historical OHLCV for ${latest?.symbol || securityId}, ${start} through ${end}; missing observations remain gaps`} />
      <div className="chart-footer"><span>{history.data.data.length.toLocaleString()} session slots · {missing} missing prices</span><span>Scroll to zoom · drag to pan · crosshair to inspect</span></div>
      {history.data.truncated && <p className="warning-text">The 5,000-session browser budget was reached. Narrow the date range.</p>}
      {missing > 0 && <p className="warning-text">Missing session prices remain empty. No forward-fill, backward-fill or interpolation is used.</p>}</>}
    </QueryState>
    {indicators.map((result, i) => <div key={features[i]}>{result.isError && <p className="warning-text">{features[i]} unavailable: {result.error.message}</p>}{result.isPending && <p className="caption">Reading {features[i]}…</p>}{result.data && <p className="caption">{features[i]}: {result.data.data.points.filter((p) => p.value !== null).length} evidenced values · {result.data.data.units} · warm-up gaps retained</p>}</div>)}
    <EvidenceNote evidence={history.data} />
  </Panel>
  {!compact && <div className="two-columns"><Panel title="Security identity" subtitle="Observed evidence, not authoritative listing intervals"><dl className="detail-grid"><dt>Stable internal ID</dt><dd className="breakable">{securityId}</dd><dt>Observed range</dt><dd>{stock.first_observed} → {stock.last_observed}</dd><dt>Observations</dt><dd>{stock.observation_count.toLocaleString()}</dd><dt>Fundamental PIT analysis</dt><dd>{stock.fundamental_pit_analysis}</dd><dt>Benchmark</dt><dd>{stock.benchmark_status}</dd></dl><EvidenceNote evidence={detail} /></Panel>
    <Panel title="Identifier continuity" subtitle="Different ISINs are never merged by ticker alone"><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table><thead><tr><th>Symbol / ISIN</th><th>First → last observed</th><th>Evidence</th></tr></thead><tbody>{stock.observed_identity_evidence.map((alias, i) => <tr key={`${alias.symbol}-${alias.first_observed}-${i}`}><td><strong>{alias.symbol}</strong><span className="cell-secondary">{alias.isin || 'No contemporaneous ISIN'}</span></td><td>{alias.first_observed}<span className="cell-secondary">{alias.last_observed}</span></td><td>{alias.identity_basis}<span className="cell-secondary">{alias.analytical_type}</span></td></tr>)}</tbody></table></div></Panel></div>}
  {!compact && history.data && <Panel title="Exact historical observations" subtitle="Most recent 12 returned slots; table values preserve source decimal precision"><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table><thead><tr><th>Session</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume</th><th>Quality</th></tr></thead><tbody>{history.data.data.slice(-12).reverse().map((r) => <tr key={r.session}><td>{r.session}</td>{[r.open, r.high, r.low, r.close, r.volume].map((value, i) => <td className="numeric" key={i}>{exact(value)}</td>)}<td><Badge tone={r.close == null ? 'warning' : 'neutral'}>{r.observation_status}</Badge><span className="cell-secondary">{r.quality}</span></td></tr>)}</tbody></table></div></Panel>}
  </>
}
