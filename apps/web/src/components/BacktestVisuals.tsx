import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { get } from '../api/client'
import { jsonObject, type Backtest } from '../api/contracts'
import { graphicNumber as parseGraphic, readable } from '../lib/format'
import { Panel, QueryState } from './ui'
import { Chart } from './Chart'
import { bars, lineChart } from '../lib/visual-options'
import { Donut, Unavailable } from './Visuals'

export function BacktestOverview({ rows }: { rows: Backtest[] }) {
  const states = [...new Set(rows.map(r => r.status))]; const scenarios = [...new Set(rows.map(r => r.cost_scenario))]
  return <div className="two-columns"><Panel title="Economic evidence coverage" subtitle="Run classifications; this distribution is not strategy performance"><Donut labels={states.map(readable)} values={states.map(s => rows.filter(r => r.status === s).length)} label="Backtest economic evidence state counts" /></Panel><Panel title="Cost scenario coverage" subtitle="Fixed historical research assumptions, not current broker charges"><Chart height={270} label="Persisted cost scenario run counts" option={bars(scenarios.map(readable), scenarios.map(s => rows.filter(r => r.cost_scenario === s).length), 'Stored runs')} /></Panel></div>
}
export function TradeVisuals({ id }: { id: string }) {
  const schema = z.object({ trades: z.array(jsonObject), counts: z.record(z.string(), z.number()), distribution: z.array(z.object({ lower: z.number(), upper: z.number(), count: z.number() })), scope: z.string() })
  const data = useQuery({ queryKey: ['backtest-trades-visual', id], queryFn: ({ signal }) => get(`/visual/backtests/${id}/trades?limit=500`, schema, signal) })
  return <QueryState query={data}>{data.data && <><p className="caption">First {data.data.data.trades.length} stored trades only. Closed-trade diagnostics do not resolve full-path economics. {data.data.page?.has_more ? 'Additional trades exist beyond this bounded page.' : ''}</p><div className="two-columns"><Panel title="Trade return distribution" subtitle="Recorded resolved trades only; excludes unresolved outcomes"><Chart height={270} label="Stored trade return histogram" option={bars(data.data.data.distribution.map(b => `${(b.lower * 100).toFixed(1)}–${(b.upper * 100).toFixed(1)}%`), data.data.data.distribution.map(b => b.count), 'Recorded trade count')} /></Panel><Panel title="Trade resolution breakdown" subtitle="Positive / negative / flat are page counts, not full-strategy win rate"><Donut labels={Object.keys(data.data.data.counts)} values={Object.values(data.data.data.counts)} label="Stored trade win loss and unresolved page counts" /></Panel><Panel title="Recorded trade chronology" subtitle="Net returns at recorded exit; no unresolved trades are filled"><Chart height={270} label="Recorded closed trade outcomes" option={bars(data.data.data.trades.map(t => String(t.exit_session || 'Unresolved')), data.data.data.trades.map(t => graphicNumber(t.net_return)), 'Net recorded raw-trade return')} /></Panel><Unavailable title="Rolling economic returns & benchmark" reason="Full-path economic comparisons remain unavailable where actions and valuation gaps are unresolved. No synthetic benchmark or strategy path." /></div></>}</QueryState>
}
export function EquityDiagnostics({ equity }: { equity: Record<string, unknown>[] }) {
  const dates = equity.map(p => String(p.session))
  return <div className="two-columns"><Panel title="Stored drawdown" subtitle="Page of persisted diagnostics; raw economics limitations remain"><Chart height={270} label="Persisted backtest drawdown" option={lineChart(dates, [{ name: 'Stored drawdown', values: equity.map(p => graphicNumber(p.drawdown)) }])} /></Panel><Panel title="Cash utilization & open exposure" subtitle="Existing stored state; no backtest recomputation"><Chart height={270} label="Stored cash utilization" option={lineChart(dates, [{ name: 'Cash utilization', values: equity.map(p => graphicNumber(p.cash_utilization)) }])} /><Chart height={230} label="Stored open position counts" option={bars(dates, equity.map(p => graphicNumber(p.open_positions)), 'Open positions')} /></Panel></div>
}

function graphicNumber(value: unknown) { return typeof value === 'string' || typeof value === 'number' || value === null ? parseGraphic(value) : null }
