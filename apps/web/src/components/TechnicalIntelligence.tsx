import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Target,
  BarChart2,
  CheckCircle2,
  Clock,
  Layers,
  Activity,
} from 'lucide-react'
import { get, queryString } from '../api/client'
import { technicalAnalysisSchema, type TechnicalAnalysisData } from '../api/nse-market'
import { Badge, Panel, QueryState, Stat } from './ui'

function scoreTone(score: number): 'positive' | 'accent' | 'warning' | 'negative' | 'neutral' {
  if (score >= 70) return 'positive'
  if (score >= 55) return 'accent'
  if (score >= 45) return 'neutral'
  if (score >= 35) return 'warning'
  return 'negative'
}

function scoreLabel(score: number): string {
  if (score >= 75) return 'STRONG BULLISH'
  if (score >= 60) return 'BULLISH'
  if (score >= 45) return 'NEUTRAL / BALANCED'
  if (score >= 30) return 'BEARISH'
  return 'STRONG BEARISH'
}

function formatInr(val: number | null | undefined): string {
  if (val == null || !Number.isFinite(val)) return 'Unavailable'
  return '₹' + val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function TechnicalIntelligence({ instrumentKey }: { instrumentKey: string }) {
  const [open, setOpen] = useState(true)
  const [showIndicators, setShowIndicators] = useState(false)

  const query = useQuery({
    queryKey: ['technical-intelligence', instrumentKey],
    retry: false,
    refetchOnWindowFocus: false,
    queryFn: ({ signal }) =>
      get(
        '/nse-market/technical-analysis?' + queryString({ key: instrumentKey }),
        technicalAnalysisSchema,
        signal
      ),
  })

  const data: TechnicalAnalysisData | undefined = query.data?.data
  const scores = data?.scores
  const plan = data?.trade_plan
  const struct = data?.chart_structure as Record<string, unknown> | undefined
  const mtf = data?.multi_timeframe as Record<string, unknown> | undefined
  const ind = data?.indicators as Record<string, unknown> | undefined
  const patterns = (data?.recent_patterns ?? []) as Array<Record<string, unknown>>

  return (
    <Panel
      className="technical-intelligence-panel"
      title="AI Technical Chart Intelligence & Profitability Engine"
      subtitle="Pure mathematical causal indicators, 15 candlestick patterns, support/resistance zones & empirical forward stats"
    >
      <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
        <summary>Inspect AI Technical Score, Empirical Patterns, Chart Structure & Trade Plan</summary>
        <QueryState query={query} label="Calculating technical indicators & pattern recognition...">
          {data && (
            <div className="technical-intelligence-content">
              {/* 1. Header Composite Score Strip */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: 'var(--surface-raised, #1b2028)',
                  padding: '1rem',
                  borderRadius: '6px',
                  marginBottom: '1rem',
                  border: '1px solid var(--border, #2d3748)',
                }}
              >
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.25rem' }}>
                    {data.symbol} · Technical Intelligence
                  </h3>
                  <span className="caption" style={{ color: 'var(--muted, #888)' }}>
                    As of session {data.as_of_session} · {data.candle_count} historical daily bars
                    analyzed
                  </span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                    <Badge tone={scoreTone(scores?.composite_technical_intelligence_score ?? 50)}>
                      {scores?.composite_technical_intelligence_score.toFixed(1)} / 100 ·{' '}
                      {scoreLabel(scores?.composite_technical_intelligence_score ?? 50)}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* 2. Subscores Grid */}
              <div className="stat-grid" style={{ marginBottom: '1.25rem' }}>
                <Stat
                  label="Trend Strength"
                  value={`${scores?.trend_score.toFixed(1)} / 100`}
                  note={String(struct?.trend_direction ?? 'CONSOLIDATION')}
                  tone={scoreTone(scores?.trend_score ?? 50)}
                />
                <Stat
                  label="Momentum"
                  value={`${scores?.momentum_score.toFixed(1)} / 100`}
                  note={
                    typeof ind?.rsi_14 === 'number'
                      ? `RSI(14): ${ind.rsi_14.toFixed(1)}`
                      : 'RSI: N/A'
                  }
                  tone={scoreTone(scores?.momentum_score ?? 50)}
                />
                <Stat
                  label="Volume Flow"
                  value={`${scores?.volume_score.toFixed(1)} / 100`}
                  note={
                    typeof ind?.relative_volume_20 === 'number'
                      ? `RVOL: ${ind.relative_volume_20.toFixed(2)}x`
                      : 'RVOL: N/A'
                  }
                  tone={scoreTone(scores?.volume_score ?? 50)}
                />
                <Stat
                  label="Candlestick Signal"
                  value={`${scores?.candlestick_score.toFixed(1)} / 100`}
                  note={`${patterns.length} recent pattern(s)`}
                  tone={scoreTone(scores?.candlestick_score ?? 50)}
                />
                <Stat
                  label="Timeframe Align"
                  value={`${scores?.timeframe_alignment_score.toFixed(1)} / 100`}
                  note={String(mtf?.timeframe_alignment ?? 'MIXED')}
                  tone={scoreTone(scores?.timeframe_alignment_score ?? 50)}
                />
                <Stat
                  label="ML Predictive Fit"
                  value={`${scores?.ml_prediction_score.toFixed(1)} / 100`}
                  note="5-session horizon"
                  tone={scoreTone(scores?.ml_prediction_score ?? 50)}
                />
              </div>

              {/* 3. Trade Plan & Execution Matrix */}
              {plan && (
                <div
                  style={{
                    background: 'var(--surface, #151921)',
                    border: '1px solid var(--border, #2d3748)',
                    borderRadius: '8px',
                    padding: '1.25rem',
                    marginBottom: '1.25rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      marginBottom: '0.75rem',
                    }}
                  >
                    <Target size={18} style={{ color: 'var(--accent, #3b82f6)' }} />
                    <h4 style={{ margin: 0, fontSize: '1.1rem' }}>
                      Quantitative Entry, Target & Risk Plan
                    </h4>
                    <Badge tone={plan.risk_classification === 'LOW' ? 'positive' : plan.risk_classification === 'MODERATE' ? 'accent' : 'warning'}>
                      {plan.risk_classification} RISK
                    </Badge>
                  </div>

                  <div className="stat-grid" style={{ marginBottom: '1rem' }}>
                    <Stat label="Reference Price" value={formatInr(plan.reference_price)} />
                    <Stat
                      label="Potential Entry Zone"
                      value={`${formatInr(plan.potential_entry_zone[0])} – ${formatInr(plan.potential_entry_zone[1])}`}
                      note="Near dynamic support"
                    />
                    <Stat
                      label="Protective Stop-Loss"
                      value={formatInr(plan.stop_loss)}
                      note={`${(((plan.stop_loss - plan.reference_price) / plan.reference_price) * 100).toFixed(2)}% risk`}
                      tone="negative"
                    />
                    <Stat
                      label="Target 1 (Conservative)"
                      value={formatInr(plan.target_1)}
                      note={`+${(((plan.target_1 - plan.reference_price) / plan.reference_price) * 100).toFixed(2)}% gain`}
                      tone="positive"
                    />
                    <Stat
                      label="Target 2 (Extended)"
                      value={formatInr(plan.target_2)}
                      note={`+${(((plan.target_2 - plan.reference_price) / plan.reference_price) * 100).toFixed(2)}% gain`}
                      tone="positive"
                    />
                    <Stat
                      label="Risk / Reward Ratio"
                      value={`1 : ${plan.risk_reward_ratio.toFixed(2)}`}
                      note={plan.risk_reward_ratio >= 1.5 ? 'Favourable R/R' : 'Marginal R/R'}
                      tone={plan.risk_reward_ratio >= 1.5 ? 'positive' : 'warning'}
                    />
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.85rem',
                      color: 'var(--muted, #888)',
                      borderTop: '1px solid var(--border-muted, #252d3a)',
                      paddingTop: '0.5rem',
                    }}
                  >
                    <span>
                      Key Support: <strong>{formatInr(plan.support_level)}</strong> · Key
                      Resistance: <strong>{formatInr(plan.resistance_level)}</strong>
                    </span>
                    <span>
                      Historical Volatility:{' '}
                      <strong>{plan.historical_volatility_pct.toFixed(1)}% annualized</strong>
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--muted, #777)',
                      margin: '0.5rem 0 0 0',
                      fontStyle: 'italic',
                    }}
                  >
                    {plan.disclaimer}
                  </p>
                </div>
              )}

              {/* 4. Candlestick Pattern Recognition */}
              <div style={{ marginBottom: '1.25rem' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    marginBottom: '0.5rem',
                  }}
                >
                  <BarChart2 size={16} />
                  <h4 style={{ margin: 0 }}>
                    Detected Candlestick Patterns ({patterns.length} in recent sessions)
                  </h4>
                </div>
                {patterns.length === 0 ? (
                  <p className="caption" style={{ color: 'var(--muted, #888)' }}>
                    No significant multi-bar candlestick pattern detected in the latest 10
                    sessions.
                  </p>
                ) : (
                  <div className="table-scroll">
                    <table style={{ width: '100%', fontSize: '0.9rem' }}>
                      <thead>
                        <tr>
                          <th>Pattern</th>
                          <th>Session</th>
                          <th>Direction</th>
                          <th>Confirmation</th>
                          <th>NSE Universe Win Rate (T+5)</th>
                          <th>Avg Net Return (T+5)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {patterns.map((p, idx) => {
                          const cls = String(p.classification ?? 'NEUTRAL')
                          const win = typeof p.empirical_win_rate_t5 === 'number' ? p.empirical_win_rate_t5 * 100 : 50
                          const netRet = typeof p.empirical_avg_net_return_t5 === 'number' ? p.empirical_avg_net_return_t5 * 100 : 0
                          return (
                            <tr key={idx}>
                              <td>
                                <strong>{String(p.pattern_name ?? 'PATTERN')}</strong>
                              </td>
                              <td>{String(p.session ?? '')}</td>
                              <td>
                                <Badge tone={cls === 'BULLISH' ? 'positive' : cls === 'BEARISH' ? 'negative' : 'neutral'}>
                                  {cls}
                                </Badge>
                              </td>
                              <td>
                                {p.confirmed ? (
                                  <span style={{ color: 'var(--positive, #10b981)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                    <CheckCircle2 size={13} /> Confirmed
                                  </span>
                                ) : (
                                  <span style={{ color: 'var(--warning, #f59e0b)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                    <Clock size={13} /> Pending Confirmation
                                  </span>
                                )}
                              </td>
                              <td>{win.toFixed(1)}%</td>
                              <td style={{ color: netRet >= 0 ? 'var(--positive, #10b981)' : 'var(--negative, #ef4444)' }}>
                                {netRet >= 0 ? `+${netRet.toFixed(2)}%` : `${netRet.toFixed(2)}%`}
                                <span className="caption" style={{ display: 'block', fontSize: '0.75rem', color: 'var(--muted, #777)' }}>
                                  after 20 bps friction
                                </span>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* 5. Chart Structure, Moving Averages & Divergences */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '1rem',
                  marginBottom: '1.25rem',
                }}
              >
                {/* Structure Box */}
                <div
                  style={{
                    background: 'var(--surface-raised, #1b2028)',
                    padding: '1rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border, #2d3748)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Layers size={16} />
                    <strong style={{ fontSize: '0.95rem' }}>Market Structure & Breakouts</strong>
                  </div>
                  <dl className="detail-grid" style={{ margin: 0 }}>
                    <dt>Primary Trend</dt>
                    <dd>{String(struct?.trend_direction ?? 'CONSOLIDATION')}</dd>
                    <dt>Price Action</dt>
                    <dd>{String(struct?.market_structure ?? 'MIXED_RANGE')}</dd>
                    <dt>Breakout Status</dt>
                    <dd>
                      {struct?.volume_confirmed_breakout ? (
                        <Badge tone="positive">Volume-Confirmed Breakout (RVOL &ge; 1.4x)</Badge>
                      ) : struct?.breakout_detected ? (
                        <Badge tone="accent">Breakout (Awaiting Volume)</Badge>
                      ) : struct?.breakdown_detected ? (
                        <Badge tone="negative">Breakdown Below Support</Badge>
                      ) : (
                        'In Trading Range'
                      )}
                    </dd>
                  </dl>
                </div>

                {/* Moving Averages & Signals */}
                <div
                  style={{
                    background: 'var(--surface-raised, #1b2028)',
                    padding: '1rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border, #2d3748)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Activity size={16} />
                    <strong style={{ fontSize: '0.95rem' }}>Crossovers & Divergences</strong>
                  </div>
                  <dl className="detail-grid" style={{ margin: 0 }}>
                    <dt>Golden / Death Cross</dt>
                    <dd>
                      {struct?.golden_cross ? (
                        <Badge tone="positive">Golden Cross (50 SMA &gt; 200 SMA)</Badge>
                      ) : struct?.death_cross ? (
                        <Badge tone="negative">Death Cross (50 SMA &lt; 200 SMA)</Badge>
                      ) : (
                        'Neutral 50/200'
                      )}
                    </dd>
                    <dt>Short-Term Momentum Cross</dt>
                    <dd>
                      {struct?.bullish_ema_cross ? (
                        <Badge tone="positive">Bullish 9/20 EMA Cross</Badge>
                      ) : struct?.bearish_ema_cross ? (
                        <Badge tone="negative">Bearish 9/20 EMA Cross</Badge>
                      ) : (
                        'Neutral 9/20'
                      )}
                    </dd>
                    <dt>Momentum Divergences</dt>
                    <dd>
                      {struct?.rsi_bullish_divergence || struct?.macd_bullish_divergence ? (
                        <Badge tone="positive">Bullish Divergence Detected</Badge>
                      ) : struct?.rsi_bearish_divergence || struct?.macd_bearish_divergence ? (
                        <Badge tone="negative">Bearish Divergence Detected</Badge>
                      ) : (
                        'No Divergence'
                      )}
                    </dd>
                  </dl>
                </div>

                {/* Multi-Timeframe Alignment */}
                <div
                  style={{
                    background: 'var(--surface-raised, #1b2028)',
                    padding: '1rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border, #2d3748)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Clock size={16} />
                    <strong style={{ fontSize: '0.95rem' }}>Multi-Timeframe Alignment</strong>
                  </div>
                  <dl className="detail-grid" style={{ margin: 0 }}>
                    <dt>Daily Trend</dt>
                    <dd>
                      <Badge tone={mtf?.daily_trend === 'BULLISH' ? 'positive' : mtf?.daily_trend === 'BEARISH' ? 'negative' : 'neutral'}>
                        {String(mtf?.daily_trend ?? 'NEUTRAL')}
                      </Badge>
                    </dd>
                    <dt>Weekly Trend</dt>
                    <dd>
                      <Badge tone={mtf?.weekly_trend === 'BULLISH' ? 'positive' : mtf?.weekly_trend === 'BEARISH' ? 'negative' : 'neutral'}>
                        {String(mtf?.weekly_trend ?? 'NEUTRAL')}
                      </Badge>
                    </dd>
                    <dt>Monthly Trend</dt>
                    <dd>
                      <Badge tone={mtf?.monthly_trend === 'BULLISH' ? 'positive' : mtf?.monthly_trend === 'BEARISH' ? 'negative' : 'neutral'}>
                        {String(mtf?.monthly_trend ?? 'NEUTRAL')}
                      </Badge>
                    </dd>
                    <dt>Overall Alignment</dt>
                    <dd>
                      <strong>{String(mtf?.timeframe_alignment ?? 'MIXED')}</strong>
                    </dd>
                  </dl>
                </div>
              </div>

              {/* 6. Technical Indicators Readout Accordion */}
              <details onToggle={(e) => setShowIndicators(e.currentTarget.open)}>
                <summary>Inspect Complete 24-Indicator Technical Values (EMA, SMA, RSI, MACD, Bollinger, ATR)</summary>
                {showIndicators && ind && (
                  <div style={{ marginTop: '0.75rem' }}>
                    <div className="stat-grid" style={{ marginBottom: '1rem' }}>
                      <Stat label="EMA 9" value={formatInr(ind.ema_9 as number)} />
                      <Stat label="EMA 20" value={formatInr(ind.ema_20 as number)} />
                      <Stat label="EMA 50" value={formatInr(ind.ema_50 as number)} />
                      <Stat label="EMA 200" value={formatInr(ind.ema_200 as number)} />
                      <Stat label="SMA 20" value={formatInr(ind.sma_20 as number)} />
                      <Stat label="SMA 50" value={formatInr(ind.sma_50 as number)} />
                      <Stat label="SMA 200" value={formatInr(ind.sma_200 as number)} />
                      <Stat
                        label="RSI (14)"
                        value={typeof ind.rsi_14 === 'number' ? ind.rsi_14.toFixed(1) : 'N/A'}
                        note={typeof ind.rsi_14 === 'number' ? (ind.rsi_14 > 70 ? 'Overbought (>70)' : ind.rsi_14 < 30 ? 'Oversold (<30)' : 'Neutral (30-70)') : ''}
                      />
                      <Stat
                        label="MACD Line"
                        value={typeof ind.macd_line === 'number' ? ind.macd_line.toFixed(2) : 'N/A'}
                      />
                      <Stat
                        label="MACD Signal"
                        value={typeof ind.macd_signal === 'number' ? ind.macd_signal.toFixed(2) : 'N/A'}
                      />
                      <Stat
                        label="MACD Histogram"
                        value={typeof ind.macd_histogram === 'number' ? ind.macd_histogram.toFixed(2) : 'N/A'}
                        tone={typeof ind.macd_histogram === 'number' && ind.macd_histogram >= 0 ? 'positive' : 'negative'}
                      />
                      <Stat
                        label="ATR (14)"
                        value={formatInr(ind.atr_14 as number)}
                        note="Average True Range"
                      />
                      <Stat
                        label="Bollinger Upper"
                        value={formatInr(ind.bollinger_upper as number)}
                      />
                      <Stat
                        label="Bollinger Lower"
                        value={formatInr(ind.bollinger_lower as number)}
                      />
                      <Stat
                        label="Stochastic %K / %D"
                        value={
                          typeof ind.stoch_k === 'number' && typeof ind.stoch_d === 'number'
                            ? `${ind.stoch_k.toFixed(1)} / ${ind.stoch_d.toFixed(1)}`
                            : 'N/A'
                        }
                      />
                      <Stat
                        label="Money Flow Index (MFI 14)"
                        value={typeof ind.mfi_14 === 'number' ? ind.mfi_14.toFixed(1) : 'N/A'}
                      />
                    </div>
                  </div>
                )}
              </details>
            </div>
          )}
        </QueryState>
      </details>
    </Panel>
  )
}
