import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ModelVisuals } from '../src/components/ModelVisuals'
import { Sparkline, Unavailable } from '../src/components/Visuals'
import { rangeStart } from '../src/lib/format'
import { lineChart } from '../src/lib/visual-options'
import { providersSchema, statisticsSchema } from '../src/api/visual'
import type { Model } from '../src/api/contracts'

vi.mock('../src/components/Chart', () => ({ Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} /> }))
const fixture: Model = { model_run_id: 'TEST_ONLY_A', model_family: 'TEST_ONLY_MODEL', task: 'classification', horizon: 1, phase: 'TEST_ONLY', fold_id: 'TEST_ONLY_FOLD', metrics: { balanced_accuracy: .5, calibration: { bins: [{ count: 3, lower: 0, upper: .5, mean_probability: .2, observed_positive_rate: .3 }] }, confusion_counts: { tp: 1, tn: 1, fp: 1, fn: 0 }, class_distribution: { '0': 2, '1': 1 } }, naive: {}, training_rows: 4, scored_test_rows: 3, beats_naive: false, model_identity: { classification: 'TEST_ONLY' } }
describe('TEST_ONLY visual semantics and interactions', () => {
  it('latest trailing year cannot default to 2010 for canonical RELIANCE', () => {
    expect(rangeStart('2026-10-06', '1Y', '2011-06-22')).toBe('2025-10-06')
    expect(rangeStart('2026-10-06', 'ALL', '2011-06-22')).toBe('2011-06-22')
  })
  it('sparkline starts a new path across missing observations', () => {
    const { container } = render(<Sparkline values={['100', null, '101', '102']} label="TEST_ONLY gap" />)
    expect(container.querySelector('path')?.getAttribute('d')?.match(/M/g)).toHaveLength(2)
    expect(screen.getByRole('img', { name: 'TEST_ONLY gap' })).toBeInTheDocument()
  })
  it('does not invent a sparkline for a one-point observation', () => {
    render(<Sparkline values={[null, '100']} label="TEST_ONLY missing" />)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText('No series')).toBeInTheDocument()
  })
  it('curve options preserve nulls and prohibit gap interpolation', () => {
    const option = lineChart(['TEST_ONLY_A', 'TEST_ONLY_B'], [{ name: 'TEST_ONLY', values: [1, null] }])
    expect(option.series).toEqual(expect.arrayContaining([expect.objectContaining({ data: [1, null], connectNulls: false })]))
  })
  it('uses stored calibration evidence and disables unsupported diagnostics', async () => {
    render(<ModelVisuals rows={[fixture, { ...fixture, model_run_id: 'TEST_ONLY_REG', task: 'regression', metrics: { mae: .1 } }]} measure="balanced_accuracy" />)
    expect(screen.getByRole('img', { name: 'Stored calibration reliability diagram' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Stored confusion matrix' })).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Diagnostic fit'), 'TEST_ONLY_REG')
    expect(screen.queryByRole('img', { name: 'Stored calibration reliability diagram' })).not.toBeInTheDocument()
    expect(screen.getByText(/no probability-bin evidence/)).toBeInTheDocument()
  })
  it('cannot parse an enabled provider into the disabled capability response', () => {
    expect(providersSchema.safeParse({ mode: 'ENABLED', acquisition_enabled: true, providers: [], capabilities: {} }).success).toBe(false)
  })
  it('does not accept a fabricated NaN statistics value', () => {
    expect(statisticsSchema.safeParse({ curve: [{ session: 'TEST_ONLY', return_1: NaN }] }).success).toBe(false)
  })
  it('unavailable widget explains why no data is plotted', () => {
    render(<Unavailable title="Live depth" reason="TEST_ONLY: provider not cleared" />)
    expect(screen.getByText('DATA UNAVAILABLE')).toBeInTheDocument()
    expect(screen.getByText('TEST_ONLY: provider not cleared')).toBeInTheDocument()
  })
})
