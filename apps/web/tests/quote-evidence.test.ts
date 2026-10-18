import { describe, expect, it } from 'vitest'
import { generationPosition } from '../src/lib/quote-evidence'

// TEST_ONLY chronology, no prices or provider observations.
describe('quote receipt explanation without classification changes', () => {
  const lower = '2026-10-18T00:00:00.100Z', upper = '2026-10-18T00:00:00.140Z'
  it('distinguishes ambiguous ordering from definitely future generation', () => {
    expect(generationPosition('2026-10-18T00:00:00.120Z', lower, upper)).toEqual({ relation: 'INSIDE_RECEIPT_UNCERTAINTY_INTERVAL', generationMinusEarliestMs: 20, intervalWidthMs: 40 })
    expect(generationPosition(upper, lower, upper)?.relation).toBe('INSIDE_RECEIPT_UNCERTAINTY_INTERVAL')
    expect(generationPosition(lower, lower, upper)?.relation).toBe('BEFORE_OR_AT_EARLIEST_RECEIPT_BOUND')
    expect(generationPosition('2026-10-18T00:00:00.141Z', lower, upper)?.relation).toBe('AFTER_LATEST_RECEIPT_BOUND')
    expect(generationPosition('2026-10-18T00:00:00.100001Z', lower, upper)?.generationMinusEarliestMs).toBe(0.001)
  })
  it('refuses incomplete, naive, contradictory or overly wide explanatory evidence', () => {
    expect(generationPosition(undefined, lower, upper)).toBeNull()
    expect(generationPosition('2026-10-18T00:00:00.120', lower, upper)).toBeNull()
    expect(generationPosition('invalidZ', lower, upper)).toBeNull()
    expect(generationPosition(lower, upper, lower)).toBeNull()
    expect(generationPosition(lower, lower, '2026-10-18T00:00:01Z')).toBeNull()
  })
})
