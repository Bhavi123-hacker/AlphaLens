import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Badge, Drawer, StockSearch } from './ui'
import { usePreferences } from '../lib/preferences'

export function QuickPalette() {
  const [open, setOpen] = useState(false); const navigate = useNavigate()
  useEffect(() => { const listener = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setOpen(v => !v) } }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener) }, [])
  return <><button className="button small palette-trigger" onClick={() => setOpen(true)}>Find instrument <kbd>Ctrl K</kbd></button>{open && <Drawer title="Instrument search palette" close={() => setOpen(false)}><StockSearch placeholder="Search canonical symbol, company or ISIN" onSelect={stock => { setOpen(false); navigate(`/stocks/${encodeURIComponent(stock.security_id)}`) }} /><p className="caption">Exact symbol / ISIN matches and latest observed canonical identities first. Archive prices are not live.</p></Drawer>}</>
}
export function WatchlistRail() {
  const preferences = usePreferences()
  return <aside className="watchlist-rail" aria-label="Browser watchlist rail"><div><strong>WATCHLIST</strong><Badge>Selected identities</Badge></div>{preferences.favorites.slice(0, 12).map(f => <NavLink key={f.security_id} to={`/stocks/${encodeURIComponent(f.security_id)}`}><strong>{f.symbol}</strong><small>{f.security_id.startsWith('upstox:') ? 'Upstox · load snapshot' : 'Archive identity'}</small></NavLink>)}{!preferences.favorites.length && <p>Add current NSE equities in the selected watchlist, or save archive favorites.</p>}<Link className="rail-link" to="/heatmap">Market Map →</Link><Link className="rail-link" to="/compare">Compare stocks →</Link></aside>
}
