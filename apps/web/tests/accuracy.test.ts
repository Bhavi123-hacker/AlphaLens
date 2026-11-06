import { describe, expect, it } from 'vitest'
import { decimalHeadline, exact, graphicNumber, partitionBacktests, rangeStart } from '../src/lib/format'
import { queryString, validateRange } from '../src/api/client'
import { priceOption } from '../src/lib/chart-options'
import { classification, priceSchema, type Indicator, type PricePoint } from '../src/api/contracts'

// Constructed TEST_ONLY fixtures. No runtime application imports these records.
const fixture: PricePoint = { session: '2023-11-10', symbol: 'TEST_ONLY_SECURITY', isin: null,
  open: '101.123456789', high: '103', low: '100', close: '102', volume: 10,
  canonical_record_id: null, quality: 'TEST_ONLY', quality_reasons: [], observation_status: 'SOURCE_ROWS_PRESENT',
  price_basis: 'RAW_UNADJUSTED', freshness: 'HISTORICAL_EOD', availability_basis: 'ASSUMED_NEXT_SESSION_AVAILABILITY' }
describe('exact values and graphic boundaries', () => {
  it('preserves all source decimal digits in tables', () => { expect(exact('12345.1234567890123456789')).toBe('12,345.1234567890123456789') })
  it('removes only value-neutral trailing zeroes in headlines', () => { expect(decimalHeadline('12345.120000000')).toBe('12,345.12'); expect(decimalHeadline('12345.123456789')).toBe('12,345.123456789') })
  it('preserves exact rational text', () => { expect(exact('5/3')).toBe('5/3'); expect(graphicNumber('5/3')).toBe(1.6667) })
  it('rounds only graphical prices at the declared boundary', () => expect(graphicNumber(fixture.open)).toBe(101.1235))
  it('rejects unsafe huge values instead of silently losing significant digits', () => expect(graphicNumber('999999999999999999999999')).toBeNull())
  it('rejects sub-resolution positive values instead of displaying a fake zero', () => expect(graphicNumber('0.000000001')).toBeNull())
  it('distinguishes genuine zero from unavailable', () => { expect(graphicNumber('0')).toBe(0); expect(graphicNumber(null)).toBeNull(); expect(exact(null)).toBe('Unavailable') })
  it('rejects nonfinite, malformed and zero-denominator values', () => { for (const value of [Infinity, 'NaN', '1/0', '1e99']) expect(graphicNumber(value)).toBeNull() })
})
describe('historical session semantics', () => {
  it('uses archive dates rather than current time for ranges', () => { expect(rangeStart('2026-10-06', '1Y', '2010-01-04')).toBe('2025-10-06'); expect(rangeStart('2026-10-06', 'ALL', '2010-01-04')).toBe('2010-01-04') })
  it('clamps month-end and available-history range boundaries', () => { expect(rangeStart('2024-03-31', '1M', '2010-01-04')).toBe('2024-02-29'); expect(rangeStart('2026-10-06', '5Y', '2024-01-01')).toBe('2024-01-01') })
  it('rejects reversed and impossible date requests', () => { expect(() => validateRange('2026-02-30', '2026-10-06')).toThrow(); expect(() => validateRange('2026-10-06', '2025-01-01')).toThrow() })
  it('encodes security identifiers and bounded query values', () => expect(queryString({ security_id: 'tejhq:isin:TEST', limit: 500, offset: 0 })).toContain('limit=500'))
  it('retains missing Muhurat slots in the chart calendar', () => {
    const missing = { ...fixture, session: '2023-11-12', open: null, high: null, low: null, close: null, volume: null }
    const option = priceOption([fixture, missing], {}, false)
    const axes = option.xAxis as Array<{ data: string[] }>; const series = option.series as Array<{ data: unknown[] }>
    expect(axes[0].data).toEqual(['2023-11-10', '2023-11-12']); expect(series[0].data[1]).toEqual(['-', '-', '-', '-']); expect(series[1].data[1]).toBeNull()
  })
  it('preserves warm-up indicator gaps and aligns stored values by session', () => {
    const indicator: Indicator = { feature: {}, units: 'INR_RAW_PRICE', points: [{ session: fixture.session, value: null, state: 'UNAVAILABLE', quality: 'TEST_ONLY', canonical_record_id: null }] }
    const option = priceOption([fixture, { ...fixture, session: '2023-11-14' }], { sma_200: indicator }, true)
    const series = option.series as Array<{ data: unknown[]; connectNulls?: boolean }>
    expect(series[2].data).toEqual([null, null]); expect(series[0].connectNulls).toBe(false)
  })
  it('uses separate linked panes for stored oscillators', () => {
    const option = priceOption([fixture], { rsi_14: { feature: {}, units: 'INDEX_0_100', points: [] } }, false)
    expect((option.grid as unknown[]).length).toBe(3); expect((option.series as Array<{ yAxisIndex?: number }>)[2].yAxisIndex).toBe(2)
  })
})
describe('research and economic evidence', () => {
  it('accepts only the open / not-cleared production gates', () => {
    const value = { data_reality: 'TEST_ONLY', usage_classification: 'TEST_ONLY', final_vintage: null, research_profile: null, p1_production_data_clearance: 'OPEN', production_market_data_use: 'NOT_CLEARED' }
    expect(classification.safeParse(value).success).toBe(true); expect(classification.safeParse({ ...value, production_market_data_use: 'PRODUCTION_APPROVED' }).success).toBe(false)
  })
  it('validates genuine missing OHLCV instead of requiring invented prices', () => expect(priceSchema.safeParse({ ...fixture, close: null }).success).toBe(true))
  it('classifies stored uncertainty reasons without estimating returns', () => {
    const status = 'UNRESOLVED_ECONOMIC_OUTCOMES'
    expect(partitionBacktests([{ status, cause_counts: { RAW_ACTION_UNRECONCILED_ECONOMIC_ENTITLEMENT: 1 } },
      { status, cause_counts: { RAW_ACTION_UNRECONCILED_ECONOMIC_ENTITLEMENT: 1, VERIFIED_SESSION_SOURCE_PRICE_MISSING: 2 } },
      { status, cause_counts: { SAME_SYMBOL_OTHER_ID_AMBIGUOUS_NOT_MERGED: 1 } }, { status: 'COMPLETE', cause_counts: {} }])).toEqual({ actions: 1, both: 1, gaps: 1, resolved: 1 })
  })
})
