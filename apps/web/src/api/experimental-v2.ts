import { z } from 'zod'
import { jsonObject } from './contracts'
import { experimentalCandidateSchema } from './experimental'

// Separate family and publication contract; a numerical score cannot confer acceptance.
export const experimentalV2WorkspaceSchema = z.object({
  schema: z.literal('alphalens.experimental_nse_v2.workspace.v1'),
  family: z.literal('ALPHALENS_EXPERIMENTAL_NSE_V2'),
  status: z.enum(['EXPERIMENTAL_UNVALIDATED', 'BACKTESTED_NOT_PROSPECTIVELY_ACCEPTED', 'PROSPECTIVE_EVALUATION_IN_PROGRESS']),
  available: z.boolean(), model: jsonObject.nullable(), dataset: jsonObject.nullable(), evaluation: jsonObject.nullable(),
  candidates: z.array(experimentalCandidateSchema.extend({
    score: z.number().finite(), risk_kind: z.string().optional(),
    feature_contributions: z.array(z.object({ feature: z.string(), observed_value: z.number().finite(), linear_contribution: z.number().finite() })).optional(),
    features: z.array(z.number().finite()).optional(), feature_names: z.array(z.string()).optional(),
  })).max(100),
  exclusions: z.array(z.union([z.string(), jsonObject])),
  prospective: z.object({ forecasts: z.number().int().nonnegative(), outcomes: z.number().int().nonnegative(), eligible_forecasts: z.number().int().nonnegative().optional(), status: z.string(), metrics: jsonObject.nullable() }).passthrough(),
  acceptance: jsonObject.optional(), accepted_current_rankings: z.literal(0),
  personalization: z.string().optional(), preference_horizon: z.string().optional(),
}).passthrough()
export type ExperimentalV2Workspace = z.infer<typeof experimentalV2WorkspaceSchema>
