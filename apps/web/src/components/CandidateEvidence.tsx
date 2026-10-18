import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { MarketCandidate } from '../api/nse-market'
import { StockResearch } from './StockResearch'
import { Badge, Drawer } from './ui'
import { SaveResearchCandidate } from './SaveResearchCandidate'
import { readable } from '../lib/format'

export function CandidateEvidence({ row }: { row: MarketCandidate }) {
  const [open, setOpen] = useState(false)
  const evidence = row.evidence
  return <><button className="button small" aria-expanded={open} onClick={() => setOpen(true)}>Why this security qualifies, risks and scenarios</button>
    {open && <Drawer title={`${row.symbol} · research evidence`} close={() => setOpen(false)}>
      <p className="breakable">{String(row.identity.name ?? row.symbol)} · {row.key}</p>
      <Badge tone="warning">{evidence?.classification ?? 'EXPERIMENTAL_ML'}</Badge>
      <p>Dated EOD close ₹{row.observed_price} · {row.session} · {row.source}. {row.data_freshness ?? 'Saved observation; separate from a current provider quote'}.</p>
      <p>V2 score <strong>{row.score.toFixed(6)}</strong>. Model target: next eligible open to fifth observed close; price component only. Scores are uncalibrated. NO_DEMONSTRATED_EDGE.</p>
      <div className="research-evidence-grid"><section><h3>Why it qualified</h3><ul>{(evidence?.why ?? ['Complete saved model inputs']).map(reason => <li key={reason}>{reason}</li>)}</ul></section>
      <p>LSTM: {row.current_lstm ? `${row.current_lstm.score.toFixed(6)} uncalibrated score, observation ${row.current_lstm.session}` : 'No compatible saved sequence score. Missing inputs are not filled.'}</p>
      <section><h3>Why it could lose money</h3><ul>{(evidence?.risks ?? ['No demonstrated economic edge']).map(reason => <li key={reason}>{reason}</li>)}</ul></section>
      <section><h3>Evidence still missing</h3><ul>{(evidence?.missing ?? row.missing_evidence).map((reason, index) => <li key={index}>{readable(reason)}</li>)}</ul></section></div>
      <SaveResearchCandidate instrumentKey={row.key}/>
      <StockResearch instrumentKey={row.key}/>
      <div className="personal-shortcuts"><Link to={'/stocks/' + encodeURIComponent('upstox:' + row.key)}>Open price, technical chart & Evidence Passport</Link><Link to="/my-portfolio">Portfolio & scenarios</Link></div>
    </Drawer>}
  </>
}
