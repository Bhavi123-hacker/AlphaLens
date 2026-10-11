import { lazy, Suspense } from 'react'
import type { EChartsCoreOption } from 'echarts/core'

const ChartCanvas = lazy(() => import('./ChartCanvas'))

export function Chart(props: { option: EChartsCoreOption; label: string; height?: number }) {
  return <Suspense fallback={<div className="chart" role="status" aria-label="Loading historical chart" style={{ height: props.height ?? 350 }}>Loading chart…</div>}><ChartCanvas {...props} /></Suspense>
}
