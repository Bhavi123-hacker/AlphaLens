import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { MarketCandidate } from '../api/nse-market'
import { ResearchSizing } from './ResearchSizing'
import { StockResearch } from './StockResearch'
import { Badge } from './ui'

export function CandidateEvidence({ row }: { row: MarketCandidate }) {
  const [open, setOpen] = useState(false)
  const evidence = row.evidence
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Why this security qualifies, risks and scenarios</summary>
    {open && <>
      <Badge tone="warning">{evidence?.classification ?? 'EXPERIMENTAL_ML'}</Badge>
      <p>{row.data_freshness ?? 'Dated saved observation'}. Model target: next observed open to fifth observed close; price component only.</p>
      <strong>Supporting observations</strong><ul>{(evidence?.why ?? ['Complete saved model inputs']).map(reason => <li key={reason}>{reason}</li>)}</ul>
      <p>LSTM: {row.current_lstm ? `${row.current_lstm.score.toFixed(6)} uncalibrated score, observation ${row.current_lstm.session}` : 'No compatible saved sequence score. Missing inputs are not filled.'}</p>
      <strong>Why it could lose money</strong><ul>{(evidence?.risks ?? ['No demonstrated economic edge']).map(reason => <li key={reason}>{reason}</li>)}</ul>
      <strong>Evidence still missing</strong><ul>{(evidence?.missing ?? row.missing_evidence).map((reason, index) => <li key={index}>{reason}</li>)}</ul>
      <ResearchSizing instrumentKey={row.key}/>
      <StockResearch instrumentKey={row.key}/>
      <Link to="/watchlists">Save through Watchlists</Link>
    </>}
  </details>
}
