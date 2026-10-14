import { z } from 'zod'

export const instrumentSchema = z.object({ provider_key: z.string(), symbol: z.string(), name: z.string().nullable(), isin: z.string(), exchange: z.literal('NSE'), segment: z.literal('NSE_EQ'), instrument_type: z.literal('EQ'), observed_at: z.string(), revision_sha256: z.string(), canonical_security_id: z.string().nullable().optional() })
export type ProviderInstrument = z.infer<typeof instrumentSchema>
export const masterSchema = z.object({ state: z.string(), observed_at: z.string().nullable(), candidate_count: z.number(), matched_count: z.number(), instruments: z.array(instrumentSchema), page: z.object({limit:z.number(),offset:z.number(),has_more:z.boolean()}).optional() })
const sessionOHLC = z.object({ session: z.string(), start_at: z.string(), open: z.string(), high: z.string(), low: z.string(), close: z.string(), volume: z.number() }).nullable()
export const snapshotItemSchema = z.object({
  state: z.string(), identity: instrumentSchema, instrument_key: z.string(), symbol: z.string(),
  source: z.string(), price_basis: z.literal('UNKNOWN'), retained: z.literal(false), received_at: z.string(),
  latest_session: z.string().nullable(), latest_close: z.string().nullable(), change: z.string().nullable(), change_percent: z.string().nullable(),
  cache_age_seconds: z.number(), cache_ttl_seconds: z.number(), streaming: z.literal(false),
  current_session_status: z.string(), official_final_close: z.string(),
  market: z.object({ state: z.string(), session: z.string(), known_at: z.string().optional(), start: z.string().optional(), end: z.string().optional() }),
  quote: z.object({ state: z.string(), ltp: z.string().optional(), previous_close: z.string().nullable().optional(), change: z.string().nullable().optional(), change_percent: z.string().nullable().optional(), snapshot_at: z.string().optional(), reported_snapshot_at: z.string().optional(), last_trade_at: z.string().optional(), freshness: z.string().optional(), clock: z.object({ local_received_at: z.string(), https_server_date: z.string().nullable(), server_minus_local_seconds: z.number().nullable(), quote_minus_local_seconds: z.number().nullable().optional(), validation: z.string() }) }),
  session_ohlc: z.object({ state: z.string(), current: sessionOHLC, previous: sessionOHLC }),
  rows: z.array(z.object({ session: z.string(), open: z.string(), high: z.string(), low: z.string(), close: z.string(), volume: z.number().int() })),
  indicators: z.record(z.string(), z.object({ units: z.string(), points: z.array(z.object({ session: z.string(), value: z.number().finite().nullable() })) })),
  passport: z.object({ identity_source: z.string(), master_revision: z.string(), retrieval_time: z.string(), publication_time: z.null(), historical_archive_joined: z.literal(false), current_inference: z.string(), blockers: z.array(z.string()) }),
})
export type ProviderSnapshot = z.infer<typeof snapshotItemSchema>
export const terminalSchema = z.object({ state: z.string(), items: z.array(snapshotItemSchema), queried_count: z.number(), full_nse_coverage: z.literal(false), retained: z.literal(false), api_calls_this_request: z.number() })
export const quoteWatchlistSchema = z.object({ state:z.string(), items:z.array(z.object({instrument_key:z.string(),symbol:z.string(),identity:instrumentSchema,quote:snapshotItemSchema.shape.quote.extend({volume:z.number().nullable().optional()}),source:z.string(),latest_session:z.string().nullable(),latest_close:z.string().nullable(),change_percent:z.string().nullable(),daily_volume:z.number().nullable(),technical:z.record(z.string(),z.number().nullable())})), selected_count:z.number(), observed_count:z.number(), valid_quote_count:z.number(),api_calls_this_request:z.number(), full_nse_coverage:z.literal(false),retained:z.literal(false),cache_ttl_seconds:z.number(),cache_age_seconds:z.number() })
