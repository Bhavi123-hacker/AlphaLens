import { graphicNumber as parseGraphic } from '../lib/format'
import { Chart } from './Chart'
import { bars, lineChart } from '../lib/visual-options'
import { Donut, Unavailable } from './Visuals'
import { Panel } from './ui'
type Row = Record<string, unknown>
function records(value: unknown): Row[] { return Array.isArray(value) ? value.filter(v => v !== null && typeof v === 'object') as Row[] : [] }
export function AccountVisuals({ state, performance, paper, rows, tab }: { state: Row; performance: Row; paper: boolean; rows: Row[]; tab: string }) {
  const positions = records(state.positions); const equity = records(performance.equity); const drawdown = records(performance.drawdown)
  const labels = positions.map(p => String(p.transaction_symbol || p.security_id))
  const known = positions.filter(p => graphicNumber(p.cost_basis) !== null && Number(graphicNumber(p.cost_basis)) > 0)
  return <div className="two-columns">{positions.length > 0 && <><Panel title="Holding cost allocation" subtitle="Recorded FIFO cost basis proxy; not current market-value allocation"><Donut labels={known.map(p => String(p.transaction_symbol || p.security_id))} values={known.map(p => graphicNumber(p.cost_basis)!)} label="Recorded holdings cost basis allocation" /></Panel><Panel title="Realized P&L by holding" subtitle="Recorded FIFO ledger; unavailable unrealized valuations stay missing"><Chart height={290} label="Recorded realized holding profit and loss" option={bars(labels, positions.map(p => graphicNumber(p.realized_pnl)), 'Realized ledger P&L')} /></Panel><Panel title="Position quantities" subtitle="Recorded positions only; not broker synchronization"><Chart height={270} label="Recorded position quantity comparison" option={bars(labels, positions.map(p => graphicNumber(p.quantity)), 'Quantity')} /></Panel></>}
    {equity.length > 0 ? <Panel title="Paper account equity" subtitle="Persisted P16 simulation evidence; no live broker P&L"><Chart label="Recorded paper account equity" option={lineChart(equity.map(p => String(p.session)), [{ name: 'Stored equity', values: equity.map(p => graphicNumber(p.equity)) }])} /></Panel> : <Unavailable title={paper ? 'Paper equity history' : 'Portfolio value history'} reason="No persisted valuation history is available in this response. Missing market values are never zero." />}
    {drawdown.length > 0 && <Panel title="Paper drawdown" subtitle="Stored drawdown state only"><Chart label="Persisted paper drawdown" option={lineChart(drawdown.map(p => String(p.session)), [{ name: 'Stored drawdown', values: drawdown.map(p => graphicNumber(p.drawdown)) }])} /></Panel>}
    {rows.length > 0 && <Panel title={tab === 'orders' ? 'Order lineage & states' : tab === 'trades' ? 'Recorded fill timeline' : 'Recorded transaction timeline'} subtitle="Bounded API page; timestamps come from persisted evidence"><Chart height={270} label="Recorded account event timeline" option={bars(rows.map(p => String(p.session || p.decision_session || 'Unavailable date')), rows.map(p => graphicNumber(p.quantity)), 'Recorded quantity')} /><div className="event-lineage">{rows.slice(0, 8).map((p, i) => <div key={String(p.order_id || p.transaction_id || i)}><span>{String(p.intent_source || p.kind || 'Persisted fill')}</span><span>→ {String(p.order_id || p.transaction_id || p.fill_id || 'Unavailable ID')}</span><span>→ {String(p.execution || p.classification || 'Recorded state')}</span></div>)}</div></Panel>}
    <Unavailable title="Benchmark / dividend / live P&L" reason="No cleared benchmark, full corporate-action ledger or live broker valuation is configured. Open/closed trade outcomes require actual persisted lifecycle evidence." />
  </div>
}

function graphicNumber(value: unknown) { return typeof value === 'string' || typeof value === 'number' || value === null ? parseGraphic(value) : null }
