import { useQuery } from '@tanstack/react-query'
import { get } from '../api/client'
import { providersSchema } from '../api/visual'
import { readable } from '../lib/format'
import { Badge, Panel, QueryState } from './ui'
export function ProviderReadiness() {
  const query = useQuery({ queryKey: ['visual-providers'], queryFn: ({ signal }) => get('/visual/providers', providersSchema, signal), staleTime: 300_000 })
  return <Panel title="Live-provider readiness" subtitle="Future read-only capability contract · no credentials, login, downloads or broker execution"><QueryState query={query}>{query.data && <><div className="two-columns">{query.data.data.providers.map(p => <div className="provider-card" key={p.name}><strong>{p.name}</strong><Badge tone="warning">{p.state}</Badge><p>Credential: {p.configured ? 'available locally' : 'not configured'} ? Account: {p.account_status} · rights: {p.rights_status}</p><p className="caption">Inactive / under-review accounts must remain blocked. Configuring credentials alone cannot clear rights or technical evidence gates.</p></div>)}</div><div className="capability-grid">{Object.entries(query.data.data.capabilities).map(([name, state]) => <div key={name}><strong>{readable(name)}</strong><Badge>{state.state}</Badge><small>{readable(state.reason)}</small></div>)}</div><p className="caption">Live acquisition is DISABLED. Future secrets belong in operator-private configuration, never frontend storage or source control.</p></>}</QueryState></Panel>
}
