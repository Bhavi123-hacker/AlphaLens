import { z } from 'zod'
import { jsonObject } from './contracts'

const strings = z.array(z.string())
const preferences = z.object({ state: z.string(), matched: strings, excluded: strings, missing: strings, unsupported: strings }).passthrough()
export const experimentalCandidateSchema = z.object({
  key: z.string().regex(/^NSE_EQ\|[A-Z0-9]{12}$/), symbol: z.string(),
  score: z.number().finite().min(0).max(1), observation_date: z.string(), source: z.string(),
  volatility_percent: z.number().finite().nullable().optional(), drawdown_percent: z.number().finite().nullable().optional(),
  preference_matches: strings.optional(), exclusions: strings.optional(), missing_evidence: strings.optional(),
  preferences: preferences.optional(), held: z.boolean().optional(), watchlisted: z.boolean().optional(),
  holdings: z.array(jsonObject).optional(), portfolio_implication: z.string().optional(),
  forecast_timing: z.string().optional(),
  freshness: z.string().optional(),
  observed_price: z.string().optional(), source_observed_at: z.string().optional(), inference_at: z.string().optional(),
  feature_contributions: z.array(z.object({ feature: z.string(), log_odds_contribution: z.number().finite(), observed_value: z.number().finite() })).optional(),
}).passthrough()
export const experimentalWorkspaceSchema = z.object({
  schema: z.literal('alphalens.experimental_nse.workspace.v1'),
  family: z.literal('ALPHALENS_EXPERIMENTAL_NSE_V1'),
  status: z.literal('EXPERIMENTAL_UNVALIDATED_RESEARCH'),
  label: z.literal('EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED'),
  available: z.boolean(), model: jsonObject.nullable(), dataset: jsonObject.nullable(),
  evaluation: jsonObject.nullable(), candidates: z.array(experimentalCandidateSchema).max(100),
  exclusions: z.array(z.union([z.string(), jsonObject])),
  prospective: z.object({ forecasts: z.number().int().nonnegative(), outcomes: z.number().int().nonnegative(), eligible_forecasts: z.number().int().nonnegative().optional(), metrics: jsonObject.nullable(), status: z.string() }).passthrough(),
  accepted_current_rankings: z.literal(0),
  personalization: z.string().optional(), preference_horizon: z.string().optional(),
}).passthrough()
export type ExperimentalWorkspace = z.infer<typeof experimentalWorkspaceSchema>
