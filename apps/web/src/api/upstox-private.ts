import { z } from 'zod'

export const privateSchema = z.object({
  state: z.string(), rows: z.array(z.object({ session: z.string(), open: z.string(), high: z.string(), low: z.string(), close: z.string(), volume: z.number().int() })), indicators: z.record(z.string(), z.object({ units: z.string(), points: z.array(z.object({ session: z.string(), value: z.number().finite().nullable() })) })),
  symbol: z.string().optional(), instrument_key: z.string().optional(), latest_session: z.string().nullable().optional(),
  latest_close: z.string().nullable().optional(), change: z.string().nullable().optional(), change_percent: z.string().nullable().optional(),
  source: z.string().optional(), price_basis: z.string().optional(), received_at: z.string().optional(), retained: z.literal(false),
  passport: z.object({ identity_source: z.string(), master_revision: z.string(), response_checksum: z.string().nullable(), retrieval_time: z.string(), publication_time: z.null(), historical_archive_joined: z.literal(false), current_inference: z.string(), blockers: z.array(z.string()) }).optional(),
  feature_readiness: z.object({ required_count: z.number(), descriptive_available_count: z.number(), model_eligible_count: z.number(), features: z.array(z.object({ column: z.string(), descriptive_value_available: z.boolean(), model_eligible: z.literal(false), exclusion: z.string() })) }).optional(),
})

