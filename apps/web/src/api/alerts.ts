import { z } from 'zod'
export const categories = ['DATA_SOURCE', 'PIPELINE', 'ML_RESEARCH', 'PORTFOLIO', 'PAPER_TRADING'] as const
export const alertSchema = z.object({
  id: z.string().regex(/^[a-f0-9]{64}$/), category: z.enum([...categories, 'STOCK_SIGNAL']),
  severity: z.enum(['INFO', 'WARNING', 'ERROR', 'CRITICAL']), title: z.string(), message: z.string(),
  lifecycle: z.enum(['NEW', 'READ', 'ACKNOWLEDGED', 'RESOLVED']),
  delivery: z.enum(['NOT_REQUESTED', 'PENDING', 'DELIVERED', 'FAILED', 'RETRY_PENDING', 'SUPPRESSED']),
  evidence_status: z.string(), created_at: z.string(), attempts: z.number(), next_attempt: z.string().nullable(),
  delivered_at: z.string().nullable(), delivery_reason: z.string().nullable(), deduplication_key: z.string(),
  channel: z.literal('IN_APP'), external_delivery: z.literal('NOT_REQUESTED'),
  history: z.array(z.object({ action: z.string(), at: z.string(), details: z.record(z.string(), z.unknown()) })).optional(), history_truncated: z.boolean().optional(),
  evidence: z.object({ code: z.string(), component: z.enum(['P19', 'P15', 'P16']), evidence_ref: z.string(),
    evidence_sha256: z.string(), event_at: z.string(), time_basis: z.enum(['PERSISTED_EVENT_TIME', 'DETECTOR_OBSERVATION_TIME']),
    run_id: z.string().nullable(), security_id: z.string().nullable(), session: z.string().nullable(),
    classification: z.string(), final_vintage: z.string().nullable(), mode: z.string(), reasons: z.array(z.string()),
  }),
})
export const preferenceSchema = z.object({
  version: z.literal('p20.preferences.v1'), categories: z.array(z.enum(categories)), include_info: z.boolean(),
  quiet_enabled: z.boolean(), quiet_start: z.string(), quiet_end: z.string(), timezone: z.literal('Asia/Kolkata'),
  cooldown_seconds: z.number().int().min(0).max(86400), maximum_attempts: z.number().int().min(1).max(5),
  retention_days: z.number().int().min(7).max(365), email: z.literal(false), desktop: z.literal(false),
})
export const alertPreferencesSchema = z.object({ preferences: preferenceSchema, mutations_enabled: z.boolean(),
  channels: z.record(z.string(), z.string()), stock_alerts: z.string(), scheduling: z.literal('DISABLED') })
export const unreadSchema = z.object({ count: z.number().int().nonnegative() })
export type Alert = z.infer<typeof alertSchema>
export type AlertPreferences = z.infer<typeof preferenceSchema>
