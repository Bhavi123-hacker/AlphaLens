import { z } from 'zod'
import { jsonObject } from './contracts'
const amount = z.string().regex(/^-?\d+(?:\.\d+)?(?:\/\d+)?$/).refine((value) => !/\/0+$/.test(value), 'Invalid exact denominator')
export const portfolioSchema = z.object({ portfolio_id: z.string(), portfolio_name: z.string(),
  portfolio_type: z.enum(['USER_RECORDED', 'PAPER']), base_currency: z.literal('INR'), created_at: z.string(),
  classification: z.string(), accounting_policy: z.object({ version: z.string(), method: z.literal('FIFO') }).passthrough() }).passthrough()
const position = z.object({ security_id: z.string(), transaction_symbol: z.string(), quantity: amount,
  cost_basis: amount, realized_pnl: amount, fees: amount, lots: z.array(jsonObject) }).passthrough()
export const holdingsSchema = z.object({ positions: z.array(position), market_value: amount.nullable(),
  unrealized_pnl: amount.nullable(), valuation_status: z.string(), risk_status: z.string(), signal_status: z.string() }).passthrough()
export const transactionsSchema = z.object({ transactions: z.array(z.object({ transaction_id: z.string(),
  kind: z.enum(['BUY', 'SELL', 'CASH_DEPOSIT', 'CASH_WITHDRAWAL', 'OPENING_POSITION']), session: z.string(),
  quantity: amount, price: amount, fees: amount, classification: z.string() }).passthrough()) }).passthrough()
export const portfolioPerformanceSchema = z.object({ accounting: z.object({ cash: amount, positions: z.array(position),
  ledger_state_id: z.string() }).passthrough(), portfolio_value: amount.nullable(), unrealized_pnl: amount.nullable(),
  total_pnl: amount.nullable(), session_pnl: amount.nullable(), performance_history: z.null(), valuation_status: z.string() }).passthrough()
const paperPerformance = z.object({ starting_capital: amount, equity: amount.nullable(), cash: amount,
  reserved_cash: amount, available_cash: amount, realized_pnl: amount, unrealized_pnl: amount.nullable(),
  total_pnl: amount.nullable(), session_pnl: amount.nullable(), fees: amount, simulated_fill_count: z.number().int(),
  classification: z.string(), freshness: z.string(), disclaimer: z.string() }).passthrough()
export const paperMetadataSchema = z.object({ portfolio: portfolioSchema, performance: paperPerformance,
  simulation_only: z.literal(true), state_id: z.string() }).passthrough()
export const paperPerformanceSchema = z.object({ performance: paperPerformance,
  equity: z.array(z.object({ session: z.string(), equity: amount.nullable(), freshness: z.string(), report_id: z.string() })),
  drawdown: z.array(z.object({ session: z.string(), drawdown: amount.nullable() })), simulation_only: z.literal(true) }).passthrough()
export const ordersSchema = z.object({ orders: z.array(z.object({ order_id: z.string(), security_id: z.string(),
  side: z.enum(['BUY', 'SELL']), decision_session: z.string(), quantity: z.number().int().nullable(),
  reserved_cash: amount, intent_source: z.enum(['MANUAL_PAPER_ORDER', 'SIGNAL_POLICY_PAPER_ORDER']),
  target: z.object({ session_date: z.string() }).passthrough() }).passthrough()), order_states: z.record(z.string(), z.string()), simulation_only: z.literal(true) }).passthrough()
export const tradesSchema = z.object({ trades: z.array(z.object({ fill_id: z.string(), order_id: z.string(), session: z.string(),
  quantity: z.number().int(), observed_open: amount, simulated_price: amount, fees: amount,
  execution: z.literal('SIMULATED_FILL_NOT_REAL_EXECUTION') }).passthrough()), simulation_only: z.literal(true) }).passthrough()
