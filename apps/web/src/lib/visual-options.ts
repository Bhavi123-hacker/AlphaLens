import type { EChartsCoreOption } from 'echarts/core'
export const colors = ['var(--chart-series-1)', 'var(--chart-series-2)', 'var(--chart-series-3)', 'var(--chart-series-4)', 'var(--chart-series-5)']
export function lineChart(dates: string[], series: { name: string; values: (number | null)[] }[], fractionDigits = 4): EChartsCoreOption {
  return { color: colors, tooltip: { trigger: 'axis', renderMode: 'richText', confine: true, valueFormatter: (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-IN', { maximumFractionDigits: fractionDigits }) : 'Unavailable' }, legend: { type: 'scroll', top: 0 }, grid: { left: 65, right: 25, top: 45, bottom: 55 }, xAxis: { type: 'category', data: dates, boundaryGap: false }, yAxis: { type: 'value', scale: true }, dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 5 }], series: series.map(s => ({ name: s.name, type: 'line', data: s.values, showSymbol: false, connectNulls: false })) }
}
export function bars(labels: string[], values: (number | null)[], name: string): EChartsCoreOption {
  return { color: colors, tooltip: { trigger: 'axis', renderMode: 'richText' }, grid: { left: 60, right: 25, top: 25, bottom: 80 }, xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30, hideOverlap: true } }, yAxis: { type: 'value' }, series: [{ name, type: 'bar', data: values, itemStyle: { borderRadius: [3, 3, 0, 0] } }] }
}
