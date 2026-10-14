import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Badge, Drawer, StockSearch } from './ui'
import { usePreferences } from '../lib/preferences'
import { ProviderSearch } from './ProviderWorkspace'

export function QuickPalette() {
  const [open, setOpen] = useState(false); const navigate = useNavigate()
  useEffect(() => { const listener = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setOpen(v => !v) } }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener) }, [])
  return <><button className="button small palette-trigger" onClick={() => setOpen(true)}>Find instrument <kbd>Ctrl K</kbd></button>{open && <Drawer title="Instrument search palette" close={() => setOpen(false)}><ProviderSearch onSelect={i=>{setOpen(false);navigate('/stocks/'+encodeURIComponent(i.canonical_security_id||'upstox:'+i.provider_key))}}/><details className="automation-diagnostics"><summary>Independent historical archive identity search</summary><StockSearch placeholder="Search canonical symbol, company or ISIN" onSelect={stock => { setOpen(false); navigate(`/stocks/${encodeURIComponent(stock.security_id)}`) }} /></details><p className="caption">Current master availability and historical identities remain separate; archive prices are not live.</p></Drawer>}</>
}
export function WatchlistRail() {
  const preferences = usePreferences()
  return <aside className="watchlist-rail" aria-label="Browser watchlist rail"><div><strong>WATCHLIST</strong><Badge>Selected identities</Badge></div>{preferences.favorites.slice(0, 12).map(f => <NavLink key={f.security_id} to={`/stocks/${encodeURIComponent(f.security_id)}`}><strong>{f.symbol}</strong><small>{f.security_id.startsWith('upstox:') ? 'Upstox · load snapshot' : 'Archive identity'}</small></NavLink>)}{!preferences.favorites.length && <p>Add current NSE equities in the selected watchlist, or save archive favorites.</p>}<Link className="rail-link" to="/heatmap">Market Map →</Link><Link className="rail-link" to="/compare">Compare stocks →</Link></aside>
}
