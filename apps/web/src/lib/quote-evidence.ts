// Explanation only. Classification belongs to the unchanged backend validator.
export function generationPosition(generated?: string, lower?: string, upper?: string) {
  const instant = (value?: string) => {
    const match = value?.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$/)
    if (!match) return null
    const whole = Date.parse(match[1] + match[3])
    return Number.isFinite(whole) ? BigInt(whole) * 1_000_000n + BigInt((match[2] ?? '').padEnd(9, '0')) : null
  }
  const [at, earliest, latest] = [generated, lower, upper].map(instant)
  if (at == null || earliest == null || latest == null || latest < earliest || latest - earliest > 100_000_000n) return null
  return {
    relation: at > latest ? 'AFTER_LATEST_RECEIPT_BOUND' : at > earliest ? 'INSIDE_RECEIPT_UNCERTAINTY_INTERVAL' : 'BEFORE_OR_AT_EARLIEST_RECEIPT_BOUND',
    generationMinusEarliestMs: Number(at - earliest) / 1_000_000,
    intervalWidthMs: Number(latest - earliest) / 1_000_000,
  }
}
