import { z } from 'zod'
import { get, queryString } from './client'
import { priceSchema } from './contracts'
const nullable = z.number().finite().nullable()
export const marketRowSchema = z.object({ security_id: z.string(), symbol: z.string(), name: z.string().nullable(), isin: z.string().nullable(), session: z.string(), close: z.string().nullable(), volume: nullable, quality: z.string(), quality_reasons: z.array(z.string()), change: z.string().nullable(), return_1: nullable, return_5: nullable.optional(), return_20: nullable.optional(), return_60: nullable.optional(), volatility_20: nullable.optional(), rsi_14: nullable.optional(), distance_sma_20: nullable.optional(), drawdown_20: nullable.optional(), momentum_percentile_20: nullable.optional(), volume_ratio_20: nullable.optional(), inference_eligibility: z.string(), risk_level: z.string(), feature_states: z.record(z.string(), z.string()), sparkline: z.array(z.object({ session: z.string(), close: z.string().nullable() })) })
export type MarketRow = z.infer<typeof marketRowSchema>
export const marketSchema = z.object({ session: z.string(), latest_stored_session: z.string(), available_sessions: z.array(z.string()), rows: z.array(marketRowSchema), coverage: z.number(), comparable: z.number(), uncomparable: z.number(), advancing: z.number(), declining: z.number(), unchanged: z.number(), mean_raw_return: nullable, interpretation: z.string(), coverage_semantics: z.string() })
export async function readMarket(session: string, signal: AbortSignal) {
  // No more than 5,000 observed identities; full summary denominator is always shown.
  let offset = 0; let last = await get(`/visual/market?${queryString({ session, limit: 500, offset })}`, marketSchema, signal)
  const rows = [...last.data.rows]
  while (last.page?.has_more && rows.length < 5000) {
    offset += last.data.rows.length
    if (!last.data.rows.length) throw new Error('Inconsistent market pagination')
    last = await get(`/visual/market?${queryString({ session, limit: 500, offset })}`, marketSchema, signal)
    rows.push(...last.data.rows)
  }
  return { ...last, data: { ...last.data, rows }, truncated: !!last.page?.has_more }
}
export const statisticsSchema = z.object({ latest: priceSchema.nullable(), curve: z.array(z.object({ session: z.string(), return_1: nullable, cumulative_return: nullable, drawdown: nullable })), distribution: z.array(z.object({ lower: z.number(), upper: z.number(), count: z.number() })), observed_high: z.string().nullable(), observed_low: z.string().nullable(), range_slots: z.number(), missing_slots: z.number(), interpretation: z.string() })
export const providersSchema = z.object({ mode: z.literal('DISABLED'), acquisition_enabled: z.literal(false), providers: z.array(z.object({ name: z.string(), configured: z.boolean(), account_status: z.string(), rights_status: z.string(), state: z.string() })), capabilities: z.record(z.string(), z.object({ state: z.string(), reason: z.string() })) })
