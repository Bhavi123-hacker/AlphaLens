import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Badge, Drawer, StockSearch } from './ui'
import { usePreferences } from '../lib/preferences'

export function QuickPalette() {
  const [open, setOpen] = useState(false); const navigate = useNavigate()
  useEffect(() => { const listener = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setOpen(v => !v) } }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener) }, [])
  return <><button className="button small palette-trigger" onClick={() => setOpen(true)}>Find instrument <kbd>Ctrl K</kbd></button>{open && <Drawer title="Instrument search palette" close={() => setOpen(false)}><StockSearch placeholder="Search canonical symbol, company or ISIN" onSelect={stock => { setOpen(false); navigate(`/stocks/${encodeURIComponent(stock.security_id)}`) }} /><p className="caption">Exact symbol / ISIN matches and latest observed canonical identities first. Archive prices are not live.</p></Drawer>}</>
}
export function WatchlistRail() {
  const preferences = usePreferences()
  return <aside className="watchlist-rail" aria-label="Browser watchlist rail"><div><strong>WATCHLIST</strong><Badge>NOT LIVE</Badge></div>{preferences.favorites.slice(0, 8).map(f => <Link key={f.security_id} to={`/stocks/${encodeURIComponent(f.security_id)}`}><strong>{f.symbol}</strong><small>{f.name || 'Dated identity'}</small></Link>)}{!preferences.favorites.length && <p>Save favorites from Market Map or Explorer. Browser-local, no broker positions.</p>}<Link className="rail-link" to="/heatmap">Market Map →</Link></aside>
}
