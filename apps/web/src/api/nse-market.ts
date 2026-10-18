import { z } from 'zod'
import { jsonObject } from './contracts'

export const universePageSchema = z.object({
  snapshot_id: z.string(), observed_at: z.string(), total: z.number().int().nonnegative(),
  page: z.number().int(), page_size: z.number().int().max(100), provider_requests: z.literal(0), summary: jsonObject,
  rows: z.array(z.object({ instrument_key: z.string(), symbol: z.string(), name: z.string().nullable(), isin: z.string(), series: z.string().optional(), eligible_common_equity: z.literal(true) }).passthrough()).max(100),
})
export const marketCandidateSchema = z.object({
  key: z.string(), symbol: z.string(), score: z.number().finite().min(0).max(1), session: z.string(),
  observed_price: z.string(), model_id: z.string(), inference_at: z.string(), source: z.string(),
  applicability: z.enum(['ORIGINAL_TRAINING_COHORT', 'OUT_OF_TRAINING_COHORT_EXTRAPOLATION_UNVALIDATED']),
  identity: jsonObject, risk: jsonObject, features: z.array(z.number().finite()), feature_names: z.array(z.string()),
  preferences: z.object({state: z.string(), matched: z.array(z.string()), excluded: z.array(z.string()), missing: z.array(z.string()), unsupported: z.array(z.string())}).optional(),
  portfolio_context: z.array(jsonObject).optional(), held: z.boolean().optional(), watchlisted: z.boolean().optional(),
  missing_evidence: z.array(z.string()),
}).passthrough()
export const marketResearchSchema = z.object({
  state: z.string(), counts: z.record(z.string(), z.number().nonnegative().nullable()), coverage: jsonObject.optional(), scores: jsonObject.nullable().optional(),
  candidates: z.array(marketCandidateSchema).max(100), total: z.number().int().nonnegative(), unfiltered_total: z.number().int().nonnegative(),
  page: z.number().int(), page_size: z.number().int().max(100), provider_requests: z.literal(0),
  accepted_current_rankings: z.literal(0), automatic_acquisition_enabled: z.literal(false),
  operations: jsonObject.optional(), prospective_cohort: jsonObject.optional(),
}).passthrough()
