import type { EChartsCoreOption } from 'echarts/core'
import { graphicNumber } from './format'
import type { Indicator, PricePoint } from '../api/contracts'

const palette = ['#50cbd5', '#8b9aff', '#d5a454', '#ee80b5', '#86c5a0']
export function priceOption(rows: PricePoint[], indicators: Record<string, Indicator>, line: boolean): EChartsCoreOption {
  const dates = rows.map((row) => row.session)
  const overlays = Object.entries(indicators).filter(([key]) => key.startsWith('sma_') || key.startsWith('ema_'))
  const oscillators = Object.entries(indicators).filter(([key]) => !key.startsWith('sma_') && !key.startsWith('ema_'))
  const panes = 2 + oscillators.length
  const mainHeight = oscillators.length ? Math.max(24, 51 - 8 * oscillators.length) : 62
  const oscillatorSpan = oscillators.length ? (90 - mainHeight - 25) / oscillators.length : 0
  const grids = [{ left: 66, right: 26, top: 36, height: `${mainHeight}%` }, { left: 66, right: 26, top: `${mainHeight + 9}%`, height: '13%' },
    ...oscillators.map((_, i) => ({ left: 66, right: 26, top: `${mainHeight + 25 + i * oscillatorSpan}%`, height: `${oscillatorSpan - 3}%` }))]
  const aligned = (indicator: Indicator) => { const values = new Map(indicator.points.map((point) => [point.session, point.value])); return dates.map((date) => values.get(date) ?? null) }
  return { color: palette, legend: { top: 0, textStyle: { color: '#99aabe', fontSize: 11 }, type: 'scroll' },
    tooltip: { trigger: 'axis', renderMode: 'richText', confine: true, backgroundColor: '#142033', borderColor: '#314157', textStyle: { color: '#e5edf6' } },
    axisPointer: { link: [{ xAxisIndex: 'all' }], label: { backgroundColor: '#334155' } }, grid: grids,
    xAxis: Array.from({ length: panes }, (_, i) => ({ type: 'category', data: dates, gridIndex: i, boundaryGap: true,
      axisLine: { lineStyle: { color: '#26364a' } }, axisTick: { show: false }, axisLabel: { show: i === panes - 1, color: '#94a3b8', fontSize: 10 }, splitLine: { show: false } })),
    yAxis: Array.from({ length: panes }, (_, i) => ({ type: 'value', gridIndex: i, scale: true,
      splitNumber: i === 1 ? 2 : 4,
      name: i === 0 ? 'INR · raw' : i === 1 ? 'Shares' : `${oscillators[i - 2][0]} · ${oscillators[i - 2][1].units}`,
      nameTextStyle: { color: '#94a3b8', fontSize: 10 }, axisLabel: { color: '#94a3b8', fontSize: 10, hideOverlap: true,
        ...(i === 1 ? { formatter: (value: number) => new Intl.NumberFormat('en', { notation: 'compact' }).format(value) } : {}) }, splitLine: { lineStyle: { color: '#243047', type: 'dashed' } } })),
    dataZoom: [{ type: 'inside', xAxisIndex: Array.from({ length: panes }, (_, i) => i), start: 0, end: 100 },
      { type: 'slider', xAxisIndex: Array.from({ length: panes }, (_, i) => i), bottom: 0, height: 18, borderColor: '#2b3b50', fillerColor: '#38bdf820', textStyle: { color: '#a5b4c7' } }],
    series: [line ? { name: 'Historical close', type: 'line', data: rows.map((r) => graphicNumber(r.close)), connectNulls: false, showSymbol: false, lineStyle: { color: palette[0], width: 2 } }
      : { name: 'OHLC', type: 'candlestick', data: rows.map((r) => { const ohlc = [r.open, r.close, r.low, r.high].map(graphicNumber); return ohlc.some((n) => n === null) ? ['-', '-', '-', '-'] : ohlc }), itemStyle: { color: '#57cda4', color0: '#f07f89', borderColor: '#57cda4', borderColor0: '#f07f89' } },
    { name: 'Volume', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: rows.map((r) => r.volume != null && Number.isSafeInteger(r.volume) ? r.volume : null), itemStyle: { color: '#4b799f80' } },
    ...overlays.map(([name, value], i) => ({ name, type: 'line', showSymbol: false, connectNulls: false, data: aligned(value), lineStyle: { color: palette[(i + 1) % palette.length], width: 1.5 } })),
    ...oscillators.map(([name, value], i) => ({ name, type: 'line', xAxisIndex: i + 2, yAxisIndex: i + 2, showSymbol: false, connectNulls: false, data: aligned(value), lineStyle: { color: palette[i % palette.length], width: 1.5 } }))],
  }
}
export function barOption(names: string[], values: (number | null)[], name: string, bounds?: [number, number]): EChartsCoreOption {
  return { grid: { left: 65, right: 25, top: 25, bottom: 90 }, tooltip: { trigger: 'axis', renderMode: 'richText', confine: true },
    xAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8', rotate: 22, fontSize: 10 } },
    yAxis: { type: 'value', scale: false, ...(bounds ? { min: bounds[0], max: bounds[1] } : {}), axisLabel: { color: '#94a3b8' }, splitLine: { lineStyle: { color: '#243047' } } },
    series: [{ name, type: 'bar', data: values, barMaxWidth: 42, itemStyle: { color: '#50cbd5', borderRadius: [3, 3, 0, 0] } }] }
}
