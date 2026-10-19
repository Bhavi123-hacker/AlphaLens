import type { EChartsCoreOption } from 'echarts/core'
import { graphicNumber } from './format'
import type { PricePoint } from '../api/contracts'

const palette = ['var(--accent)', 'var(--chart-series-2)', 'var(--chart-series-3)', 'var(--chart-series-4)', 'var(--chart-series-6)']
export function priceTooltip(parameters: unknown): string {
  const entries = (Array.isArray(parameters) ? parameters : [parameters]) as { axisValueLabel?: string; seriesName?: string; seriesType?: string; data?: unknown }[]
  const number = (v: unknown) => typeof v === 'number' && Number.isFinite(v) ? new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v) : 'Unavailable'
  return [entries[0]?.axisValueLabel || '', ...entries.map(p => p.seriesType === 'candlestick' && Array.isArray(p.data) ? `OHLC  O ${number(p.data[0])}  H ${number(p.data[3])}  L ${number(p.data[2])}  C ${number(p.data[1])}` : `${p.seriesName}: ${p.seriesName === 'Volume' && typeof p.data === 'number' ? p.data.toLocaleString('en-IN') : number(p.data)}`)].join('\n')
}
type ChartPrice = Pick<PricePoint, 'session' | 'open' | 'high' | 'low' | 'close' | 'volume'>
type ChartIndicator = { feature?: unknown; units: string; points: { session: string; value: number | null; state?: string; quality?: string; canonical_record_id?: string | null }[] }
export function priceOption(rows: ChartPrice[], indicators: Record<string, ChartIndicator>, line: boolean): EChartsCoreOption {
  const dates = rows.map((row) => row.session)
  const overlays = Object.entries(indicators).filter(([key]) => key.startsWith('sma_') || key.startsWith('ema_') || key.startsWith('bollinger_upper') || key.startsWith('bollinger_lower'))
  const oscillators = Object.entries(indicators).filter(([key]) => !key.startsWith('sma_') && !key.startsWith('ema_') && !key.startsWith('bollinger_upper') && !key.startsWith('bollinger_lower'))
  const panes = 2 + oscillators.length
  const mainHeight = oscillators.length ? Math.max(24, 51 - 8 * oscillators.length) : 62
  const oscillatorSpan = oscillators.length ? (90 - mainHeight - 25) / oscillators.length : 0
  const grids = [{ left: 66, right: 26, top: 36, height: `${mainHeight}%` }, { left: 66, right: 26, top: `${mainHeight + 9}%`, height: '13%' },
    ...oscillators.map((_, i) => ({ left: 66, right: 26, top: `${mainHeight + 25 + i * oscillatorSpan}%`, height: `${oscillatorSpan - 3}%` }))]
  const aligned = (indicator: ChartIndicator) => { const values = new Map(indicator.points.map((point) => [point.session, point.value])); return dates.map((date) => values.get(date) ?? null) }
  return { color: palette, legend: { top: 0, textStyle: { color: 'var(--muted)', fontSize: 11 }, type: 'scroll' },
    tooltip: { trigger: 'axis', renderMode: 'richText', confine: true, formatter: priceTooltip, backgroundColor: 'var(--surface-raised)', borderColor: 'var(--border)', textStyle: { color: 'var(--text)', fontSize: 13 } },
    axisPointer: { link: [{ xAxisIndex: 'all' }], label: { backgroundColor: 'var(--border)' } }, grid: grids,
    xAxis: Array.from({ length: panes }, (_, i) => ({ type: 'category', data: dates, gridIndex: i, boundaryGap: true,
      axisLine: { lineStyle: { color: 'var(--border)' } }, axisTick: { show: false }, axisLabel: { show: i === panes - 1, color: 'var(--muted)', fontSize: 10 }, splitLine: { show: false } })),
    yAxis: Array.from({ length: panes }, (_, i) => ({ type: 'value', gridIndex: i, scale: true,
      splitNumber: i === 1 ? 2 : 4,
      name: i === 0 ? 'INR · raw' : i === 1 ? 'Shares' : `${oscillators[i - 2][0]} · ${oscillators[i - 2][1].units}`,
      nameTextStyle: { color: 'var(--muted)', fontSize: 12 }, axisLabel: { color: 'var(--muted)', fontSize: 12, hideOverlap: true,
        ...(i === 1 ? { formatter: (value: number) => new Intl.NumberFormat('en', { notation: 'compact' }).format(value) } : {}) }, splitLine: { lineStyle: { color: 'var(--border-muted)', type: 'dashed' } } })),
    dataZoom: [{ type: 'inside', xAxisIndex: Array.from({ length: panes }, (_, i) => i), start: 0, end: 100 },
      { type: 'slider', xAxisIndex: Array.from({ length: panes }, (_, i) => i), bottom: 0, height: 18, borderColor: 'var(--border)', fillerColor: 'var(--chart-area)', textStyle: { color: 'var(--muted)' } }],
    series: [line ? { name: 'Historical close', type: 'line', data: rows.map((r) => graphicNumber(r.close)), connectNulls: false, showSymbol: false, lineStyle: { color: palette[0], width: 2 } }
      : { name: 'OHLC', type: 'candlestick', data: rows.map((r) => { const ohlc = [r.open, r.close, r.low, r.high].map(graphicNumber); return ohlc.some((n) => n === null) ? ['-', '-', '-', '-'] : ohlc }), itemStyle: { color: 'var(--positive)', color0: 'var(--negative)', borderColor: 'var(--positive)', borderColor0: 'var(--negative)' } },
    { name: 'Volume', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: rows.map((r) => r.volume != null && Number.isSafeInteger(r.volume) ? r.volume : null), itemStyle: { color: 'var(--chart-volume)' } },
    ...overlays.map(([name, value], i) => ({ name, type: 'line', showSymbol: false, connectNulls: false, data: aligned(value), lineStyle: { color: palette[(i + 1) % palette.length], width: 1.5 } })),
    ...oscillators.map(([name, value], i) => ({ name, type: name === 'macd_histogram' ? 'bar' : 'line', xAxisIndex: i + 2, yAxisIndex: i + 2, showSymbol: false, connectNulls: false, data: aligned(value), lineStyle: { color: palette[i % palette.length], width: 1.5 } }))],
  }
}
export function barOption(names: string[], values: (number | null)[], name: string, bounds?: [number, number]): EChartsCoreOption {
  return { grid: { left: 65, right: 25, top: 25, bottom: 90 }, tooltip: { trigger: 'axis', renderMode: 'richText', confine: true },
    xAxis: { type: 'category', data: names, axisLabel: { color: 'var(--muted)', rotate: 22, fontSize: 10 } },
    yAxis: { type: 'value', scale: false, ...(bounds ? { min: bounds[0], max: bounds[1] } : {}), axisLabel: { color: 'var(--muted)' }, splitLine: { lineStyle: { color: 'var(--border-muted)' } } },
    series: [{ name, type: 'bar', data: values, barMaxWidth: 42, itemStyle: { color: 'var(--accent)', borderRadius: [3, 3, 0, 0] } }] }
}
