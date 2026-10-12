import { z } from 'zod'

export const dailyStatusSchema = z.object({
  configured: z.boolean(), pipeline_status: z.string(), live_data_activation: z.literal('BLOCKED'),
  scheduled_execution: z.literal('DISABLED'), latest_attempted_session: z.string().nullable(),
  latest_successful_research_session: z.string().nullable(), last_source_receipt: z.string().nullable(),
  freshness: z.string(), feature_readiness: z.string(), inference_readiness: z.string(),
  ranking_status: z.string(), signal_status: z.string(), historical_replay_count: z.number().int(),
  provider: z.object({ status: z.string(), revision: z.string(), reasons: z.array(z.string()) }).passthrough(),
  production_ready: z.literal(false),
})
export const dailyRunSchema = z.object({
  run_id: z.string().regex(/^[a-f0-9]{64}$/), mode: z.enum(['DAILY', 'HISTORICAL_REPLAY', 'TEST_ONLY']),
  session: z.string(), state: z.string(), source_received_at: z.string(),
  started_at: z.string(), completed_at: z.string(), reasons: z.array(z.string()),
  data_reality: z.string(), usage_classification: z.string(), coverage_scope: z.string(),
  inference_status: z.string(), ranking_status: z.string(), signal_status: z.string(),
}).passthrough()

export const prospectiveStatusSchema = z.object({
  configured: z.boolean(), forecasts: z.number().int().nonnegative(),
  pending: z.number().int().nonnegative(), resolved: z.number().int().nonnegative(),
  unresolved: z.number().int().nonnegative(), inference: z.literal('UNAVAILABLE'),
  shortlist: z.literal('UNAVAILABLE'), scheduler: z.literal('DISABLED'),
  reasons: z.array(z.string()), metrics: z.unknown().nullable(),
})
