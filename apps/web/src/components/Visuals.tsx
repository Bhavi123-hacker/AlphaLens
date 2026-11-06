import { Chart } from './Chart'
import { Empty, Panel } from './ui'

const colors = ['var(--chart-series-3)', '#f47686', 'var(--chart-series-3)', 'var(--chart-series-3)', '#f0c875']
export function Donut({ labels, values, label }: { labels: string[]; values: number[]; label: string }) {
  return <Chart height={270} label={label} option={{ color: colors, tooltip: { trigger: 'item', renderMode: 'richText' }, legend: { bottom: 0, type: 'scroll' }, series: [{ type: 'pie', radius: ['48%', '72%'], center: ['50%', '44%'], label: { show: false }, data: labels.map((name, i) => ({ name, value: values[i] })) }] }} />
}
export function Unavailable({ title, reason }: { title: string; reason: string }) { return <Panel title={title} className="capability-card"><Empty title="DATA UNAVAILABLE"><p>{reason}</p></Empty></Panel> }
export function Sparkline({ values, label }: { values: (string | null)[]; label: string }) {
  const nums = values.map(v => v === null ? null : Number(v)); const valid = nums.filter((v): v is number => v !== null && Number.isFinite(v))
  if (valid.length < 2) return <span className="caption">No series</span>
  const low = Math.min(...valid), high = Math.max(...valid); const scale = high - low || 1
  // Each missing observation starts a new path; no gap is silently joined.
  const path = nums.map((v, i) => { if (v === null || !Number.isFinite(v)) return ''; const cmd = i === 0 || nums[i - 1] === null || !Number.isFinite(nums[i - 1]) ? 'M' : 'L'; return `${cmd}${i * 100 / Math.max(1, nums.length - 1)},${28 - (v - low) / scale * 24}` }).join(' ')
  return <svg className="sparkline" viewBox="0 0 100 32" role="img" aria-label={label}><path d={path} fill="none" stroke={valid.at(-1)! >= valid[0] ? 'var(--positive)' : 'var(--negative)'} strokeWidth="1.7" /></svg>
}
