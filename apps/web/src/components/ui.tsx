import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { AlertTriangle, ArrowUpRight, ChevronLeft, ChevronRight, Search, RefreshCw, X, Database, FileCheck2 } from 'lucide-react'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { z } from 'zod'
import { APIError, get, queryString } from '../api/client'
import { stockSchema, type Evidence, type Stock } from '../api/contracts'
import { useDebounce } from '../lib/useDebounce'
import { readable } from '../lib/format'

export function Heading({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div><div className="heading-description">{children}</div></div>
}
export function Panel({ title, subtitle, actions, children, className = '' }: { title?: string; subtitle?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{title && <div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{actions}</div>}{children}</section>
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'positive' | 'warning' | 'negative' | 'accent' }) { return <span className={`badge badge-${tone}`}>{children}</span> }
export function Empty({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Database size={25} /></div><h3>{title}</h3><div>{children}</div>{action}</div>
}
export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) {
  const api = error instanceof APIError ? error : undefined
  return <div className="error-state" role="status"><AlertTriangle size={20} /><div><h3>{api?.status === 503 ? 'Evidence unavailable' : api?.status === 404 ? 'Record not found' : 'Unable to read evidence'}</h3><p>{error.message}</p>
    {api?.reasons.length ? <ul>{api.reasons.map((reason) => <li key={reason}>{readable(reason)}</li>)}</ul> : null}
    {api?.evidence && <span className="caption">{api.evidence.classification.usage_classification} · {api.evidence.source}</span>}
    {retry && <button className="button small" onClick={retry}><RefreshCw size={14} />Retry read</button>}</div></div>
}
export function QueryState({ query, children, label = 'Loading stored evidence' }: { query: UseQueryResult<unknown, Error>; children: ReactNode; label?: string }) {
  if (query.isPending) return <div className="skeleton-block" aria-label={label} role="status"><span /><span /><span /><p>{label}</p></div>
  if (query.isError) return <ErrorState error={query.error} retry={() => void query.refetch()} />
  return <>{children}</>
}
export function EvidenceNote({ evidence }: { evidence?: Evidence<unknown> }) {
  if (!evidence) return null
  return <details className="evidence-note"><summary><FileCheck2 size={14} />Source & evidence <span>{evidence.classification.usage_classification}</span></summary>
    <dl className="detail-grid"><dt>Source</dt><dd>{evidence.source}</dd><dt>As of session</dt><dd>{evidence.as_of_session ?? 'Not session-specific'}</dd>
      <dt>Data reality</dt><dd>{evidence.classification.data_reality}</dd><dt>Quality</dt><dd>{evidence.quality_status}</dd>
      <dt>Vintage</dt><dd>{evidence.classification.final_vintage ?? 'Not applicable'}</dd><dt>Profile</dt><dd>{evidence.classification.research_profile ?? 'Not applicable'}</dd>
      <dt>Artifact</dt><dd className="breakable">{evidence.artifact_id ?? evidence.version}</dd></dl>
    {evidence.missing_data_reasons.length > 0 && <ul>{evidence.missing_data_reasons.map((reason) => <li key={reason}>{readable(reason)}</li>)}</ul>}
    {Object.keys(evidence.provenance).length > 0 && <details className="technical-details"><summary>Source lineage and pinned versions</summary><pre>{JSON.stringify(evidence.provenance, null, 2)}</pre></details>}
  </details>
}
export function Stat({ label, value, note, tone }: { label: string; value: ReactNode; note?: string; tone?: string }) {
  return <div className="stat"><span className="stat-label">{label}</span><strong className={tone ?? ''}>{value}</strong>{note && <span className="caption">{note}</span>}</div>
}
export function Pager({ offset, limit, more, setOffset, count }: { offset: number; limit: number; more: boolean; setOffset: (offset: number) => void; count: number }) {
  return <div className="pager"><span>{count ? `${offset + 1}–${offset + count}` : 'No records'} · Stable identity order</span><div>
    <button className="button small" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}><ChevronLeft size={16} />Previous</button>
    <button className="button small" disabled={!more || offset + limit > 10000} onClick={() => setOffset(offset + limit)}>Next<ChevronRight size={16} /></button></div></div>
}
export function StockSearch({ onSelect, placeholder = 'Search symbol, name or ISIN', compact = false }: { onSelect: (stock: Stock) => void; placeholder?: string; compact?: boolean }) {
  const [search, setSearch] = useState(''); const [open, setOpen] = useState(false); const [active, setActive] = useState(-1)
  const debounced = useDebounce(search); const id = useId(); const root = useRef<HTMLDivElement>(null)
  const query = useQuery({ queryKey: ['stocks', debounced, 8], queryFn: ({ signal }) => get(`/stocks?${queryString({ q: debounced, limit: 8 })}`, z.array(stockSchema), signal), enabled: open })
  const rows = query.data?.data ?? []
  useEffect(() => { const close = (event: MouseEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false) }; document.addEventListener('mousedown', close); return () => document.removeEventListener('mousedown', close) }, [])
  const choose = (stock: Stock) => { onSelect(stock); setOpen(false); setSearch(''); setActive(-1) }
  return <div className={`stock-search ${compact ? 'compact-search' : ''}`} ref={root}><Search size={17} /><input aria-label={placeholder} placeholder={placeholder} value={search} maxLength={100}
    role="combobox" aria-expanded={open} aria-controls={`${id}-list`} aria-autocomplete="list" aria-activedescendant={active >= 0 && rows[active] ? `${id}-${active}` : undefined}
    onFocus={() => setOpen(true)} onChange={(event) => { setSearch(event.target.value); setOpen(true); setActive(-1) }}
    onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false); if (event.key === 'ArrowDown') { event.preventDefault(); setOpen(true); setActive((i) => Math.min(rows.length - 1, i + 1)) }
      if (event.key === 'ArrowUp') { event.preventDefault(); setActive((i) => Math.max(0, i - 1)) } if (event.key === 'Enter' && rows[active]) { event.preventDefault(); choose(rows[active]) } }} />
    {open && <div className="search-popover"><ul id={`${id}-list`} role="listbox" aria-label="Security search results">
      {rows.map((stock, i) => <li key={stock.security_id} id={`${id}-${i}`} role="option" aria-selected={active === i} onMouseDown={(event) => event.preventDefault()}>
        <button tabIndex={-1} className={active === i ? 'active' : ''} onClick={() => choose(stock)}><div><strong>{stock.latest_observed_symbol || 'Unnamed security'}</strong><span>{stock.latest_observed_name || 'Name not evidenced'}</span><span title={stock.security_id}>{stock.latest_observed_isin || `Provisional · ${stock.security_id.slice(0, 54)}`}</span></div><ArrowUpRight size={16} /></button></li>)}
    </ul>{query.isPending && <p className="search-message">Searching genuine records…</p>}{query.isError && <p className="search-message">{query.error.message}</p>}{query.isSuccess && !rows.length && <p className="search-message">No matching recorded identities.</p>}</div>}
  </div>
}
export function Drawer({ title, close, children }: { title: string; close: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { const current = dialog.current; current?.showModal(); return () => current?.close() }, [])
  return <dialog ref={dialog} className="drawer" aria-label={title} onCancel={close} onClick={(event) => { if (event.target === event.currentTarget) close() }}><div className="drawer-inner"><div className="panel-heading"><h2>{title}</h2><button className="icon-button" aria-label="Close details" onClick={close}><X /></button></div>{children}</div></dialog>
}
