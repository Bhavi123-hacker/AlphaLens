import { expect, it } from 'vitest'
import { resolveChartTokens } from '../src/lib/chart-theme'

it('resolves nested theme colors while preserving actual values, missingness and formatters', () => {
  const formatter = () => 'TEST_ONLY'
  const option = { series: [{ data: [0, null, -1.2345], itemStyle: { color: 'var(--positive)' } }], tooltip: { formatter } }
  const styles = { getPropertyValue: () => '#91E5A3' }
  const result = resolveChartTokens(option, styles)
  expect(result.series[0].itemStyle.color).toBe('#91E5A3')
  expect(result.series[0].data).toEqual(option.series[0].data)
  expect(result.tooltip.formatter).toBe(formatter)
  expect(option.series[0].itemStyle.color).toBe('var(--positive)')
  expect(resolveChartTokens(option, { getPropertyValue: () => '#246538' }).series[0].itemStyle.color).toBe('#246538')
})
