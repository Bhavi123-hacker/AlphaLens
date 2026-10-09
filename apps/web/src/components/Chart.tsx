import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, CandlestickChart, LineChart, ScatterChart } from 'echarts/charts'
import { AriaComponent, AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsCoreOption } from 'echarts/core'
import { usePreferences } from '../lib/preferences'
echarts.use([BarChart, CandlestickChart, LineChart, ScatterChart, AriaComponent, AxisPointerComponent, DataZoomComponent, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

export function Chart({ option, label, height = 350 }: { option: EChartsCoreOption; label: string; height?: number }) {
  const { theme } = usePreferences()
  const element = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  useEffect(() => {
    if (!element.current) return
    const instance = echarts.init(element.current, undefined, { renderer: 'canvas' }); chart.current = instance
    const observer = new ResizeObserver(() => instance.resize()); observer.observe(element.current)
    return () => { observer.disconnect(); instance.dispose(); chart.current = null }
  }, [])
  useEffect(() => {
    const styles = window.getComputedStyle(document.documentElement)
    const muted = styles.getPropertyValue('--muted').trim(), text = styles.getPropertyValue('--text').trim(), border = styles.getPropertyValue('--border').trim()
    const axes = (value: unknown) => (Array.isArray(value) ? value : value ? [value] : []).map((axis: Record<string, unknown>) => ({ ...axis,
      axisLabel: { ...(axis.axisLabel as object), color: muted }, nameTextStyle: { ...(axis.nameTextStyle as object), color: muted },
      splitLine: { ...(axis.splitLine as object), lineStyle: { color: border, type: 'dashed' } } }))
    chart.current?.setOption({ ...option, animation: false, backgroundColor: 'transparent',
      xAxis: axes(option.xAxis), yAxis: axes(option.yAxis),
      tooltip: { ...(option.tooltip as object), backgroundColor: styles.getPropertyValue('--surface-raised').trim(), borderColor: border, textStyle: { color: text } },
      legend: { ...(option.legend as object), textStyle: { color: muted, fontSize: 11 } },
      textStyle: { fontFamily: 'Inter Variable, sans-serif', color: muted }, aria: { enabled: true } }, { notMerge: true })
  }, [option, theme])
  return <div className="chart" ref={element} role="img" aria-label={label} style={{ height }} data-testid="financial-chart" />
}
