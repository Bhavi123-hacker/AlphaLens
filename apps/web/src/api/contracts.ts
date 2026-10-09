import { z } from 'zod'
import type { components, paths } from './generated'

export type APIRoutes = keyof paths
export type PricePoint = components['schemas']['PricePoint']
export type PredictionPoint = components['schemas']['PredictionPoint']
export const jsonObject = z.record(z.string(), z.unknown())
export type JsonObject = z.infer<typeof jsonObject>
export const classification = z.object({ data_reality: z.string(), usage_classification: z.string(),
  final_vintage: z.string().nullable(), research_profile: z.string().nullable(),
  p1_production_data_clearance: z.literal('OPEN'), production_market_data_use: z.literal('NOT_CLEARED') })
export function envelope<S extends z.ZodType>(data: S) {
  return z.object({ data, source: z.string(), as_of_session: z.string().nullable(),
    classification, version: z.string(), artifact_id: z.string().nullable(),
    provenance: jsonObject, evidence_status: z.string(), quality_status: z.string(),
    missing_data_reasons: z.array(z.string()),
    page: z.object({ limit: z.number().int(), offset: z.number().int(), has_more: z.boolean(), total: z.number().int().nullable() }).nullable() })
}
export type Evidence<T> = Omit<z.infer<ReturnType<typeof envelope>>, 'data'> & { data: T }
export const stockSchema = z.object({ security_id: z.string(), first_observed: z.string(),
  last_observed: z.string(), observation_count: z.number().int(), latest_observed_symbol: z.string().optional(),
  latest_observed_name: z.string().optional(), latest_observed_isin: z.string().optional(),
  analytical_type: z.string().optional(), identity_basis: z.string().optional() }).passthrough()
export type Stock = z.infer<typeof stockSchema>
export const aliasSchema = z.object({ security_id: z.string(), symbol: z.string(), isin: z.string(), name: z.string(),
  analytical_type: z.string(), identity_basis: z.string(), first_observed: z.string(), last_observed: z.string() }).passthrough()
export const detailSchema = stockSchema.extend({ observed_identity_evidence: z.array(aliasSchema),
  identity_semantics: z.string(), fundamental_pit_analysis: z.string(), benchmark_status: z.string(), price_basis: z.literal('RAW_UNADJUSTED') })
export type StockDetail = z.infer<typeof detailSchema>
export const priceSchema = z.object({ session: z.string(), symbol: z.string().nullable(), isin: z.string().nullable(),
  open: z.string().nullable(), high: z.string().nullable(), low: z.string().nullable(), close: z.string().nullable(),
  volume: z.number().int().nullable(), canonical_record_id: z.string().nullable(), quality: z.string(),
  quality_reasons: z.array(z.string()), observation_status: z.string(), price_basis: z.literal('RAW_UNADJUSTED'),
  freshness: z.literal('HISTORICAL_EOD'), availability_basis: z.literal('ASSUMED_NEXT_SESSION_AVAILABILITY') }) satisfies z.ZodType<PricePoint>
export const indicatorPointSchema = z.object({ session: z.string(), value: z.number().finite().nullable(),
  state: z.string(), quality: z.string(), canonical_record_id: z.string().nullable() })
export const indicatorSchema = z.object({ feature: jsonObject, units: z.string(), points: z.array(indicatorPointSchema) })
export type Indicator = z.infer<typeof indicatorSchema>
const nullableMetric = z.number().finite().nullable()
export const modelSchema = z.object({ model_run_id: z.string(), model_family: z.string(), task: z.enum(['classification', 'regression']),
  horizon: z.union([z.literal(1), z.literal(5), z.literal(10), z.literal(20)]), phase: z.string(), fold_id: z.string(),
  metrics: z.record(z.string(), z.unknown()), naive: jsonObject,
  training_rows: z.number(), scored_test_rows: z.number(), beats_naive: z.boolean(), model_identity: jsonObject }).passthrough()
export type Model = z.infer<typeof modelSchema>
export const comparisonSchema = z.object({ models: z.array(jsonObject), selected: z.record(z.string(), jsonObject),
  confirmation: z.unknown(), final_holdout: z.unknown(), final_holdout_evaluated: z.boolean() }).passthrough()
export const backtestSchema = z.object({ backtest_id: z.string(), cause_counts: z.record(z.string(), z.number()),
  horizon: z.number(), model_family: z.string(), phase: z.string(), selection_rule: z.string(), cost_scenario: z.string(),
  status: z.string(), task: z.string(), unresolved_trade_count: z.number(), unknown_valuation_sessions: z.number() }).passthrough()
export type Backtest = z.infer<typeof backtestSchema>
export const equityPointSchema = z.object({ session: z.string(), portfolio_value: z.string().nullable(),
  total_pnl: z.string().nullable(), drawdown: nullableMetric, quality: z.string() }).passthrough()
export const backtestDetailSchema = z.object({ summary: jsonObject, economic_evidence: backtestSchema })
export const backtestPerformanceSchema = backtestDetailSchema.extend({ equity: z.array(equityPointSchema), benchmark_status: z.string() })
export const predictionSchema = z.object({ security_id: z.string(), session_date: z.string(), decision_time: z.string(),
  prediction_id: z.string(), model_id: z.string(), task: z.string(), horizon: z.union([z.literal(1), z.literal(5), z.literal(10), z.literal(20)]),
  fold_id: z.string(), phase: z.string(), score: nullableMetric, prediction: nullableMetric,
  canonical_record_id: z.string(), role: z.literal('FOLD_TEST'), interpretation: z.literal('PERSISTED_OOS_RESEARCH_NOT_LIVE_SIGNAL') }) satisfies z.ZodType<PredictionPoint>

export const featureControls = [
  ['sma_20', 'SMA 20', 'price'], ['sma_50', 'SMA 50', 'price'], ['sma_100', 'SMA 100', 'price'], ['sma_200', 'SMA 200', 'price'],
  ['ema_12', 'EMA 12', 'price'], ['ema_26', 'EMA 26', 'price'], ['rsi_14', 'RSI 14', 'oscillator'],
  ['macd', 'MACD', 'oscillator'], ['macd_signal', 'MACD signal', 'oscillator'], ['macd_histogram', 'MACD histogram', 'oscillator'],
  ['atr_14', 'ATR 14', 'oscillator'], ['volatility_20', 'Volatility 20', 'oscillator'],
  ['volume_ratio_20', 'Volume ratio 20', 'oscillator'], ['bollinger_location_20', 'Bollinger location', 'oscillator'],
  ['bollinger_width_20', 'Bollinger width', 'oscillator'],
] as const
