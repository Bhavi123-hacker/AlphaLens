import { z } from 'zod'
import { jsonObject } from './contracts'

export const universePageSchema = z.object({
  snapshot_id: z.string(), observed_at: z.string(), total: z.number().int().nonnegative(),
  page: z.number().int(), page_size: z.number().int().max(100), provider_requests: z.literal(0), summary: jsonObject,
  identity_status: z.object({state:z.enum(['FRESH','STALE']),observed_at:z.string(),current_identity_actions_available:z.boolean(),discovery_available:z.literal(true)}).optional(),
  rows: z.array(z.object({ instrument_key: z.string(), symbol: z.string(), name: z.string().nullable(), isin: z.string(), series: z.string().optional(), eligible_common_equity: z.literal(true) }).passthrough()).max(100),
})
export const marketCandidateSchema = z.object({
  key: z.string(), symbol: z.string(), score: z.number().finite().min(0).max(1), session: z.string(),
  observed_price: z.string(), model_id: z.string(), inference_at: z.string(), source: z.string(),
  original_forecast_recorded_at: z.string().optional(),
  entry_session: z.string().optional(), entry_open_at: z.string().optional(),
  applicability: z.enum(['ORIGINAL_TRAINING_COHORT', 'OUT_OF_TRAINING_COHORT_EXTRAPOLATION_UNVALIDATED']),
  identity: jsonObject, risk: jsonObject, features: z.array(z.number().finite()), feature_names: z.array(z.string()),
  preferences: z.object({state: z.string(), matched: z.array(z.string()), excluded: z.array(z.string()), missing: z.array(z.string()), unsupported: z.array(z.string())}).optional(),
  portfolio_context: z.array(jsonObject).optional(), held: z.boolean().optional(), watchlisted: z.boolean().optional(),
  evidence: z.object({why:z.array(z.string()),risks:z.array(z.string()),missing:z.array(z.string()),classification:z.string(),ml_horizon_sessions:z.literal(5)}).optional(),
  current_lstm: z.object({score:z.number().finite().min(0).max(1),model_sha256:z.string(),session:z.string(),inference_at:z.string(),calibration_status:z.string()}).nullable().optional(),
  data_freshness:z.string().optional(),volatility_percent:z.number().finite().nullable().optional(),drawdown_percent:z.number().finite().nullable().optional(),
  missing_evidence: z.array(z.string()),
}).passthrough()
export const marketResearchSchema = z.object({
  state: z.string(), counts: z.record(z.string(), z.number().nonnegative().nullable()), coverage: jsonObject.optional(), scores: jsonObject.nullable().optional(),
  candidates: z.array(marketCandidateSchema).max(100), total: z.number().int().nonnegative(), unfiltered_total: z.number().int().nonnegative(),
  page: z.number().int(), page_size: z.number().int().max(100), provider_requests: z.literal(0),
  accepted_current_rankings: z.literal(0), automatic_acquisition_enabled: z.boolean(),
  operations: jsonObject.optional(), prospective_cohort: jsonObject.optional(),
  research_horizon_sessions:z.union([z.literal(5),z.literal(10),z.literal(20)]).optional(),
  ranking_basis:z.enum(['EXPERIMENTAL_FIVE_SESSION_MODEL_SCORE','EXPERIMENTAL_FIVE_SESSION_SCORE_MINUS_DAILY_VOLATILITY','DESCRIPTIVE_LOW_DAILY_VOLATILITY_NOT_HORIZON_FORECAST']).optional(),
  ranking_policy:jsonObject.optional(), recommendation_eligibility:jsonObject.optional(),
  ml_horizon_supported:z.boolean().optional(),
}).passthrough().superRefine((value,ctx)=>{
  const scheduler=value.operations?.scheduler as Record<string,unknown>|undefined
  if(value.automatic_acquisition_enabled && scheduler?.state!=='REGISTERED_ENABLED_LAST_VERIFIED')ctx.addIssue({code:'custom',message:'Enabled collection requires verified scheduler evidence'})
})
export type MarketCandidate = z.infer<typeof marketCandidateSchema>

export const technicalAnalysisSchema = z.object({
  security_key: z.string(),
  symbol: z.string(),
  as_of_session: z.string(),
  candle_count: z.number().int(),
  scores: z.object({
    trend_score: z.number(),
    momentum_score: z.number(),
    volume_score: z.number(),
    candlestick_score: z.number(),
    volatility_risk_score: z.number(),
    timeframe_alignment_score: z.number(),
    ml_prediction_score: z.number(),
    composite_technical_intelligence_score: z.number(),
  }),
  trade_plan: z.object({
    reference_price: z.number(),
    potential_entry_zone: z.array(z.number()),
    support_level: z.number(),
    resistance_level: z.number(),
    stop_loss: z.number(),
    target_1: z.number(),
    target_2: z.number(),
    risk_reward_ratio: z.number(),
    expected_t5_return_pct: z.number(),
    expected_t10_return_pct: z.number(),
    historical_volatility_pct: z.number(),
    risk_classification: z.string(),
    disclaimer: z.string(),
  }),
  indicators: jsonObject,
  chart_structure: jsonObject,
  multi_timeframe: jsonObject,
  recent_patterns: z.array(jsonObject),
})
export type TechnicalAnalysisData = z.infer<typeof technicalAnalysisSchema>
