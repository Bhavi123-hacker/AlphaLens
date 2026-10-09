import { useDebounce } from '../lib/useDebounce'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Search, Star } from 'lucide-react'
import { z } from 'zod'
import { get, queryString } from '../api/client'
import { stockSchema } from '../api/contracts'
import { toggleFavorite, usePreferences } from '../lib/preferences'
import { Badge, Empty, EvidenceNote, Heading, Pager, Panel, QueryState, StockSearch } from '../components/ui'
import { StockWorkspace } from '../components/StockWorkspace'

export function Explorer() {
  const [search, setSearch] = useState(''); const [offset, setOffset] = useState(0); const q = useDebounce(search)
  const preferences = usePreferences()
  const query = useQuery({ queryKey: ['explorer', q, offset], queryFn: ({ signal }) => get(`/stocks?${queryString({ q, limit: 25, offset })}`, z.array(stockSchema), signal) })
  return <><Heading eyebrow="Historical market intelligence" title="Market explorer">Discover securities through dated identities.<br />Historical observations, never live quotes.</Heading>
    {preferences.favorites.length > 0 && <div className="favorite-strip"><span className="caption">BROWSER FAVORITES</span>{preferences.favorites.map((favorite) => <Link className="chip" key={favorite.security_id} to={`/stocks/${encodeURIComponent(favorite.security_id)}`}><Star size={12} />{favorite.symbol}</Link>)}</div>}
    <Panel title="Security directory" subtitle="Symbol, name, ISIN and stable internal ID" actions={<Badge tone="accent">P5 research identities</Badge>}>
      <div className="explorer-toolbar"><label className="search-field"><Search size={18} /><input aria-label="Search securities" placeholder="Search securities, companies or ISINs…" maxLength={100} value={search} onChange={(e) => { setSearch(e.target.value); setOffset(0) }} /></label><span className="caption">Sort: stable security ID ↑</span></div>
      <QueryState query={query}>{query.data && (query.data.data.length ? <><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable evidence table"><table className="stock-table"><thead><tr><th aria-label="Favorite" /><th>Security</th><th>Identity & classification</th><th>Observed coverage</th><th className="numeric">Observations</th><th aria-label="Open analysis" /></tr></thead><tbody>{query.data.data.map((stock) => {
        const selected = preferences.favorites.some((favorite) => favorite.security_id === stock.security_id)
        return <tr key={stock.security_id}><td><button className={`icon-button ${selected ? 'favorited' : ''}`} aria-label={`${selected ? 'Remove' : 'Save'} favorite ${stock.latest_observed_symbol}`} aria-pressed={selected} onClick={() => toggleFavorite({ security_id: stock.security_id, symbol: stock.latest_observed_symbol || stock.security_id, name: stock.latest_observed_name || '' })}><Star size={15} /></button></td>
          <td><Link className="security-link" to={`/stocks/${encodeURIComponent(stock.security_id)}`}>{stock.latest_observed_symbol || 'Unnamed identity'}</Link><span className="cell-secondary">{stock.latest_observed_name || 'Name not evidenced'}</span></td><td>{stock.latest_observed_isin || <Badge tone="warning">Provisional identity</Badge>}<span className="cell-secondary">{stock.analytical_type}</span><span className="cell-secondary breakable">{stock.security_id}</span></td><td>{stock.first_observed}<span className="cell-secondary">through {stock.last_observed}</span></td><td className="numeric">{stock.observation_count.toLocaleString()}</td><td><Link className="icon-button" aria-label={`Analyze ${stock.latest_observed_symbol}`} to={`/stocks/${encodeURIComponent(stock.security_id)}`}><ArrowUpRight size={18} /></Link></td></tr>
      })}</tbody></table></div><Pager offset={offset} limit={25} more={query.data.page?.has_more ?? false} setOffset={setOffset} count={query.data.data.length} /></> : <Empty title="No recorded identities match">Try a symbol, company name or ISIN. Securities with different ISINs stay distinct.</Empty>)}<EvidenceNote evidence={query.data} /></QueryState>
    </Panel></>
}
export function Analysis() {
  const params = useParams(); const navigate = useNavigate(); const id = params.security_id
  return <><Heading eyebrow="Security workspace" title="Stock analysis">Explore observed prices and stored P6 indicators.<br />Raw prices do not include total-return adjustments.</Heading>
    <div className="analysis-selector"><StockSearch onSelect={(stock) => navigate(`/stocks/${encodeURIComponent(stock.security_id)}`)} placeholder="Select a security for analysis" /><Badge tone="warning">RESEARCH ONLY</Badge></div>
    {id ? <StockWorkspace securityId={id} /> : <Panel><Empty title="Open a research workspace">Choose a security by symbol, name or ISIN to inspect its genuine historical observations.<div className="empty-action"><Link className="button primary" to="/market">Browse market explorer<ArrowUpRight size={16} /></Link></div></Empty></Panel>}</>
}
